/* Supplemental controlled-peer checks. This process is not Android adbd. */
package com.flyfishxu.kadb.validation.peer;

import static com.flyfishxu.kadb.validation.peer.IosPairingPeer.*;

import com.flyfish233.crypto.spake2.Spake2Context;
import com.flyfish233.crypto.spake2.Spake2Role;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.EOFException;
import java.net.InetAddress;
import java.net.SocketException;
import java.net.SocketTimeoutException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.security.cert.X509Certificate;
import java.security.interfaces.RSAPublicKey;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import javax.crypto.AEADBadTagException;
import javax.crypto.Cipher;
import javax.net.ssl.SSLException;
import javax.net.ssl.SSLServerSocket;
import javax.net.ssl.SSLSocket;
import org.conscrypt.Conscrypt;

/** Explicit fault injection, with successful recovery in the same Native consumer process. */
public final class M3PairingPeer {
    private static final List<String> CASES = List.of(
            "positive_seed", "wrong_code", "stale_exporter", "wrong_role", "missing_identity_nul",
            "invalid_spake_length", "invalid_header", "bad_gcm_tag", "invalid_peer_info",
            "network_disconnect", "timeout", "cancellation", "positive_recovery");

    public static void main(String[] arguments) throws Exception {
        require(arguments.length == 1, "Pass a new ready-file path");
        Path ready = Path.of(arguments[0]).toAbsolutePath();
        require(!Files.exists(ready), "Ready file already exists");
        Files.createDirectories(ready.getParent());
        String temporaryCode = System.getenv("KADB_M3_PAIRING_CODE");
        require(temporaryCode != null && temporaryCode.matches("[0-9]{6}"), "Missing ephemeral M3 pairing code");
        byte[] seedExporter = null;
        var records = new ArrayList<String>();
        int accepted = 0;
        int tlsCompleted = 0;
        try (SSLServerSocket server = (SSLServerSocket) createContext().getServerSocketFactory()
                .createServerSocket(0, 2, InetAddress.getByName("127.0.0.1"))) {
            server.setEnabledProtocols(new String[]{"TLSv1.3"});
            server.setNeedClientAuth(true);
            server.setSoTimeout(30_000);
            Path temporary = ready.resolveSibling(ready.getFileName() + ".tmp");
            Files.writeString(temporary, Integer.toString(server.getLocalPort()));
            Files.move(temporary, ready, StandardCopyOption.ATOMIC_MOVE);
            for (String scenario : CASES) {
                long started = System.nanoTime();
                try (SSLSocket socket = (SSLSocket) server.accept()) {
                    accepted++;
                    System.out.println("KADB_PAIRING_SESSION_JSON {\"case\":\"" + scenario
                            + "\",\"event\":\"accepted\",\"ordinal\":" + accepted + "}");
                    socket.setSoTimeout(8_000);
                    socket.startHandshake();
                    require(socket.getSession().getProtocol().equals("TLSv1.3"), "Unexpected TLS protocol");
                    tlsCompleted++;
                    System.out.println("KADB_PAIRING_SESSION_JSON {\"case\":\"" + scenario
                            + "\",\"event\":\"tls_completed\",\"ordinal\":" + tlsCompleted + "}");
                    byte[] binding = Conscrypt.exportKeyingMaterial(socket, "adb-label\0", null, 64);
                    require(binding != null && binding.length == 64, "Incorrect TLS exporter length");
                    try {
                        if (scenario.equals("positive_seed")) seedExporter = binding.clone();
                        if (scenario.equals("stale_exporter")) {
                            require(seedExporter != null && !Arrays.equals(seedExporter, binding),
                                    "Replay case needs two demonstrably different real TLS exporters");
                        }
                        String stage = exchange(socket, scenario, binding, seedExporter, temporaryCode);
                        String closure = List.of("wrong_code", "stale_exporter", "wrong_role",
                                "missing_identity_nul", "network_disconnect").contains(scenario)
                                ? "peer_initiated" : "client_initiated";
                        String record = "{\"case\":\"" + scenario + "\",\"status\":\"passed\",\"stage\":\""
                                + stage + "\",\"closure\":\"" + closure + "\",\"elapsed_ms\":"
                                + (System.nanoTime() - started) / 1_000_000 + "}";
                        records.add(record);
                        System.out.println("KADB_PAIRING_CASE_JSON " + record);
                        System.out.println("PASS controlled_peer_" + scenario + " stage=" + stage);
                    } finally {
                        Arrays.fill(binding, (byte) 0);
                    }
                }
            }
        } finally {
            if (seedExporter != null) Arrays.fill(seedExporter, (byte) 0);
            Files.deleteIfExists(ready);
            System.out.println("KADB_PAIRING_PEER_JSON {\"status\":\""
                    + (records.size() == CASES.size() ? "passed" : "failed") + "\",\"sessions_executed\":"
                    + accepted + ",\"completed_sessions\":" + records.size() + ",\"positive_sessions\":"
                    + records.stream().filter(record -> record.contains("positive_")).count()
                    + ",\"negative_sessions_completed\":"
                    + records.stream().filter(record -> !record.contains("positive_")).count()
                    + ",\"tls_sessions_completed\":" + tlsCompleted + ",\"expected_negative_sessions\":11,"
                    + "\"tls\":\"TLSv1.3\",\"real_adbd\":false,\"cases\":[" + String.join(",", records) + "]}");
        }
    }

    private static String exchange(SSLSocket socket, String scenario, byte[] binding, byte[] seedExporter,
                                   String temporaryCode)
            throws Exception {
        var input = new DataInputStream(socket.getInputStream());
        var output = new DataOutputStream(socket.getOutputStream());
        byte[] clientMessage = readFrame(input, 0);
        require(clientMessage.length == 32, "Incorrect SPAKE25519 client message size");
        if (scenario.equals("network_disconnect")) return "peer_closes_after_client_spake";
        if (scenario.equals("timeout") || scenario.equals("cancellation")) {
            long started = System.nanoTime();
            requireClientClosed(input);
            require((System.nanoTime() - started) / 1_000_000 < 8_000, "Client close exceeded bound");
            return "client_closed_stalled_exchange";
        }
        if (scenario.equals("invalid_spake_length")) {
            writeFrame(output, 0, new byte[31]);
            requireClientClosed(input);
            return "client_rejected_31_byte_spake";
        }
        if (scenario.equals("invalid_header")) {
            output.writeByte(2); // Actual unsupported wire version; no EOF until client rejects it.
            output.writeByte(0);
            output.writeInt(32);
            output.write(new byte[32]);
            output.flush();
            requireClientClosed(input);
            return "client_rejected_header_version_2";
        }
        byte[] password = concat(utf8(temporaryCode), scenario.equals("stale_exporter") ? seedExporter : binding);
        byte[] serverIdentity = utf8(scenario.equals("missing_identity_nul") ? "adb pair server" : "adb pair server\0");
        var peer = new Spake2Context(scenario.equals("wrong_role") ? Spake2Role.Alice : Spake2Role.Bob,
                serverIdentity, utf8("adb pair client\0"));
        byte[] key = null;
        try {
            writeFrame(output, 0, peer.generateMessage(password));
            key = deriveKey(peer.processMessage(clientMessage));
            byte[] encrypted = readFrame(input, 1);
            if (List.of("wrong_code", "stale_exporter", "wrong_role", "missing_identity_nul").contains(scenario)) {
                boolean rejected = false;
                try {
                    byte[] unexpected = crypt(Cipher.DECRYPT_MODE, key, encrypted);
                    Arrays.fill(unexpected, (byte) 0);
                } catch (AEADBadTagException expected) {
                    rejected = true;
                }
                require(rejected, "Mismatched transcript unexpectedly authenticated");
                return "peer_gcm_rejected_client_authentication";
            }
            byte[] info = crypt(Cipher.DECRYPT_MODE, key, encrypted);
            try {
                var certificate = (X509Certificate) socket.getSession().getPeerCertificates()[0];
                byte[] expectedKey = adbPublicKey((RSAPublicKey) certificate.getPublicKey(), "kadb-ios-interop");
                require(info.length == 8192 && info[0] == 0, "Incorrect client PeerInfo");
                require(Arrays.equals(Arrays.copyOfRange(info, 1, 1 + expectedKey.length), expectedKey),
                        "PeerInfo differs from TLS client certificate");
                for (int i = 1 + expectedKey.length; i < info.length; i++) require(info[i] == 0, "Nonzero padding");
            } finally {
                Arrays.fill(info, (byte) 0);
            }
            byte[] response = new byte[8192];
            response[0] = (byte) (scenario.equals("invalid_peer_info") ? 0 : 1);
            byte[] guid = utf8("adb-m3-controlled-peer\0");
            System.arraycopy(guid, 0, response, 1, guid.length);
            byte[] protectedResponse = crypt(Cipher.ENCRYPT_MODE, key, response);
            try {
                if (scenario.equals("bad_gcm_tag")) protectedResponse[protectedResponse.length - 1] ^= 1;
                writeFrame(output, 1, protectedResponse);
            } finally {
                Arrays.fill(response, (byte) 0);
                Arrays.fill(protectedResponse, (byte) 0);
            }
            requireClientClosed(input);
            return scenario.startsWith("positive_") ? "valid_peer_info_and_client_close"
                    : scenario.equals("bad_gcm_tag") ? "client_rejected_corrupt_gcm_tag"
                    : "client_rejected_wrong_peer_info_type";
        } finally {
            peer.destroy();
            Arrays.fill(password, (byte) 0);
            if (key != null) Arrays.fill(key, (byte) 0);
        }
    }

    private static void requireClientClosed(DataInputStream input) throws Exception {
        try {
            require(input.read() == -1, "Client sent extra bytes instead of closing failed session");
        } catch (SocketTimeoutException timeout) {
            throw new IllegalStateException("Client did not close its session within 8s", timeout);
        } catch (EOFException | SocketException | SSLException closed) {
            // Native close may send close_notify or reset; both establish transport release.
        }
    }
}
