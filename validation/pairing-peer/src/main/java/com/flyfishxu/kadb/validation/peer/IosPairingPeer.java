/*
 * Derived from Kadb's Apache-2.0 validation peer at 75678915fd4bdd52345edbb6bc4913ae3415a680.
 * Reference SPAKE mathematics remain in the separate, unmodified GPL-3.0 Java artifact.
 */
package com.flyfishxu.kadb.validation.peer;

import com.flyfish233.crypto.spake2.Spake2Context;
import com.flyfish233.crypto.spake2.Spake2Role;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.math.BigInteger;
import java.net.InetAddress;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.KeyPairGenerator;
import java.security.KeyStore;
import java.security.SecureRandom;
import java.security.cert.X509Certificate;
import java.security.interfaces.RSAPublicKey;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.Arrays;
import java.util.Base64;
import java.util.Date;
import javax.crypto.AEADBadTagException;
import javax.crypto.Cipher;
import javax.crypto.Mac;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;
import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLServerSocket;
import javax.net.ssl.SSLSocket;
import javax.net.ssl.X509TrustManager;
import org.bouncycastle.asn1.x500.X500Name;
import org.bouncycastle.cert.jcajce.JcaX509CertificateConverter;
import org.bouncycastle.cert.jcajce.JcaX509v3CertificateBuilder;
import org.bouncycastle.jce.provider.BouncyCastleProvider;
import org.bouncycastle.operator.jcajce.JcaContentSignerBuilder;
import org.conscrypt.Conscrypt;

/** Independent test server; accepts only loopback and exits unless both required sessions finish. */
public final class IosPairingPeer {
    public static void main(String[] arguments) throws Exception {
        require(arguments.length == 1, "Pass the new ready-file path");
        Path ready = Path.of(arguments[0]).toAbsolutePath();
        require(!Files.exists(ready), "Ready file already exists");
        Files.createDirectories(ready.getParent());
        SSLContext context = createContext();
        try (SSLServerSocket server = (SSLServerSocket) context.getServerSocketFactory()
                .createServerSocket(0, 2, InetAddress.getByName("127.0.0.1"))) {
            server.setEnabledProtocols(new String[]{"TLSv1.3"});
            server.setNeedClientAuth(true);
            server.setSoTimeout(60_000);
            Path temporary = ready.resolveSibling(ready.getFileName() + ".tmp");
            Files.writeString(temporary, Integer.toString(server.getLocalPort()));
            Files.move(temporary, ready, StandardCopyOption.ATOMIC_MOVE);
            for (int session = 0; session < 2; session++) {
                try (SSLSocket socket = (SSLSocket) server.accept()) {
                    exchange(socket, session == 1);
                }
            }
        } finally {
            Files.deleteIfExists(ready);
        }
        System.out.println("KADB_PAIRING_PEER_JSON {\"status\":\"passed\",\"sessions_executed\":2,"
                + "\"positive_sessions\":1,\"wrong_code_rejections\":1,\"tls\":\"TLSv1.3\","
                + "\"spake_reference\":\"spake2-java@809ad7aa731f475c07763b1ad2c165ae192dfb5f\"}");
    }

    private static SSLContext createContext() throws Exception {
        KeyPairGenerator generator = KeyPairGenerator.getInstance("RSA");
        generator.initialize(2048);
        var keyPair = generator.generateKeyPair();
        var provider = new BouncyCastleProvider();
        var subject = new X500Name("CN=Kadb independent pairing reference");
        Instant now = Instant.now();
        var certificate = new JcaX509CertificateConverter().setProvider(provider).getCertificate(
                new JcaX509v3CertificateBuilder(subject, new BigInteger(128, new SecureRandom()).add(BigInteger.ONE),
                        Date.from(now.minus(1, ChronoUnit.DAYS)), Date.from(now.plus(1, ChronoUnit.DAYS)),
                        subject, keyPair.getPublic()).build(
                        new JcaContentSignerBuilder("SHA256withRSA").setProvider(provider).build(keyPair.getPrivate())));
        certificate.verify(keyPair.getPublic());
        var store = KeyStore.getInstance(KeyStore.getDefaultType());
        store.load(null, null);
        store.setKeyEntry("peer", keyPair.getPrivate(), new char[0], new X509Certificate[]{certificate});
        var managers = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
        managers.init(store, new char[0]);
        // Test-only trust policy: the protocol below binds PeerInfo to the presented client key.
        var trust = new X509TrustManager() {
            public void checkClientTrusted(X509Certificate[] chain, String type) { }
            public void checkServerTrusted(X509Certificate[] chain, String type) { }
            public X509Certificate[] getAcceptedIssuers() { return new X509Certificate[0]; }
        };
        var context = SSLContext.getInstance("TLSv1.3", Conscrypt.newProvider());
        context.init(managers.getKeyManagers(), new X509TrustManager[]{trust}, null);
        return context;
    }

    private static void exchange(SSLSocket socket, boolean wrongCode) throws Exception {
        socket.setSoTimeout(10_000);
        socket.startHandshake();
        require(socket.getSession().getProtocol().equals("TLSv1.3"), "Unexpected TLS protocol");
        var certificate = (X509Certificate) socket.getSession().getPeerCertificates()[0];
        byte[] publicKey = adbPublicKey((RSAPublicKey) certificate.getPublicKey(), "kadb-ios-interop");
        byte[] binding = Conscrypt.exportKeyingMaterial(socket, "adb-label\0", null, 64);
        require(binding != null && binding.length == 64, "Incorrect TLS exporter length");
        byte[] password = concat(utf8("123456"), binding);
        var bob = new Spake2Context(Spake2Role.Bob, utf8("adb pair server\0"), utf8("adb pair client\0"));
        try {
            byte[] message = bob.generateMessage(password);
            var input = new DataInputStream(socket.getInputStream());
            var output = new DataOutputStream(socket.getOutputStream());
            byte[] clientMessage = readFrame(input, 0);
            require(clientMessage.length == 32, "Incorrect SPAKE25519 message size");
            writeFrame(output, 0, message);
            byte[] key = deriveKey(bob.processMessage(clientMessage));
            try {
                byte[] encrypted = readFrame(input, 1);
                if (wrongCode) {
                    boolean rejected = false;
                    try {
                        byte[] unexpected = crypt(Cipher.DECRYPT_MODE, key, encrypted);
                        Arrays.fill(unexpected, (byte) 0);
                    } catch (AEADBadTagException expected) {
                        rejected = true;
                    }
                    require(rejected, "Wrong pairing code unexpectedly authenticated");
                } else {
                    byte[] info = crypt(Cipher.DECRYPT_MODE, key, encrypted);
                    try {
                        require(info.length == 8192 && info[0] == 0, "Incorrect client PeerInfo");
                        require(Arrays.equals(Arrays.copyOfRange(info, 1, 1 + publicKey.length), publicKey),
                                "PeerInfo key/name differs from the TLS client certificate");
                        for (int i = 1 + publicKey.length; i < info.length; i++) {
                            require(info[i] == 0, "Non-zero PeerInfo padding");
                        }
                        byte[] response = new byte[8192];
                        response[0] = 1;
                        byte[] guid = utf8("adb-jvm-peer-guid\0");
                        System.arraycopy(guid, 0, response, 1, guid.length);
                        writeFrame(output, 1, crypt(Cipher.ENCRYPT_MODE, key, response));
                    } finally {
                        Arrays.fill(info, (byte) 0);
                    }
                }
            } finally {
                Arrays.fill(key, (byte) 0);
            }
        } finally {
            bob.destroy();
            Arrays.fill(binding, (byte) 0);
            Arrays.fill(password, (byte) 0);
        }
    }

    /** AOSP android_pubkey wire representation, independently encoded with JCA BigInteger. */
    private static byte[] adbPublicKey(RSAPublicKey key, String name) {
        require(key.getModulus().bitLength() == 2048, "ADB requires a 2048-bit RSA key");
        BigInteger modulus = key.getModulus();
        BigInteger r32 = BigInteger.ONE.shiftLeft(32);
        var encoded = ByteBuffer.allocate(524).order(ByteOrder.LITTLE_ENDIAN);
        encoded.putInt(64);
        encoded.putInt(r32.subtract(modulus.mod(r32).modInverse(r32)).intValue());
        putLittleEndian(encoded, modulus, 256);
        putLittleEndian(encoded, BigInteger.ONE.shiftLeft(4096).mod(modulus), 256);
        encoded.putInt(key.getPublicExponent().intValueExact());
        return concat(Base64.getEncoder().encode(encoded.array()), utf8(" " + name + "\0"));
    }

    private static void putLittleEndian(ByteBuffer target, BigInteger value, int bytes) {
        require(value.signum() >= 0 && value.bitLength() <= bytes * 8, "Public integer exceeds field size");
        for (int i = 0; i < bytes; i++) target.put(value.shiftRight(i * 8).byteValue());
    }

    private static byte[] deriveKey(byte[] material) throws Exception {
        var hmac = Mac.getInstance("HmacSHA256");
        hmac.init(new SecretKeySpec(new byte[32], "HmacSHA256"));
        byte[] extracted;
        try {
            extracted = hmac.doFinal(material);
        } finally {
            Arrays.fill(material, (byte) 0);
        }
        try {
            hmac.init(new SecretKeySpec(extracted, "HmacSHA256"));
            byte[] block = hmac.doFinal(concat(utf8("adb pairing_auth aes-128-gcm key"), new byte[]{1}));
            try { return Arrays.copyOf(block, 16); }
            finally { Arrays.fill(block, (byte) 0); }
        } finally {
            Arrays.fill(extracted, (byte) 0);
        }
    }

    private static byte[] crypt(int mode, byte[] key, byte[] value) throws Exception {
        var cipher = Cipher.getInstance("AES/GCM/NoPadding");
        cipher.init(mode, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, new byte[12]));
        return cipher.doFinal(value);
    }

    private static byte[] readFrame(DataInputStream input, int type) throws Exception {
        require(input.readUnsignedByte() == 1 && input.readUnsignedByte() == type, "Incorrect pairing header");
        int size = input.readInt(); // network byte order, including the unsigned size bound
        require(size > 0 && size <= 16384, "Invalid pairing payload size");
        byte[] bytes = new byte[size];
        input.readFully(bytes);
        return bytes;
    }

    private static void writeFrame(DataOutputStream output, int type, byte[] payload) throws Exception {
        output.writeByte(1);
        output.writeByte(type);
        output.writeInt(payload.length);
        output.write(payload);
        output.flush();
    }

    private static byte[] utf8(String text) { return text.getBytes(StandardCharsets.UTF_8); }

    private static byte[] concat(byte[] first, byte[] second) {
        byte[] combined = Arrays.copyOf(first, first.length + second.length);
        System.arraycopy(second, 0, combined, first.length, second.length);
        return combined;
    }

    private static void require(boolean condition, String description) {
        if (!condition) throw new IllegalStateException(description);
    }
}
