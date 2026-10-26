package com.flyfishxu.kadb.validation.runtime;

import android.app.Activity;
import android.app.Instrumentation;
import android.os.Build;
import android.os.Bundle;
import android.os.Process;
import com.flyfishxu.kadb.Kadb;
import com.flyfishxu.kadb.cert.InMemoryPrivateKeyStore;
import com.flyfishxu.kadb.cert.KadbCert;
import com.flyfishxu.kadb.cert.KadbCertException;
import com.flyfishxu.kadb.cert.KadbCertPolicy;
import com.flyfishxu.kadb.cert.KadbIdentitySnapshot;
import com.flyfishxu.kadb.cert.OkioFilePrivateKeyStore;
import java.io.ByteArrayInputStream;
import java.io.File;
import java.io.IOException;
import java.security.cert.CertificateFactory;
import java.security.cert.X509Certificate;
import java.security.interfaces.RSAPublicKey;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import javax.net.ssl.SSLContext;
import kotlin.Unit;
import kotlin.coroutines.Continuation;
import kotlin.coroutines.EmptyCoroutineContext;
import kotlin.jvm.functions.Function2;
import kotlinx.coroutines.BuildersKt;
import kotlinx.coroutines.CoroutineScope;
import kotlinx.coroutines.TimeoutKt;
import okio.FileSystem;
import org.json.JSONArray;
import org.json.JSONObject;

/** Self-instrumenting emulator consumer. Every check uses the public Android API. */
public final class RuntimeInstrumentation extends Instrumentation {
    private final List<String> checks = new ArrayList<>();
    private final List<byte[]> privateCopies = new ArrayList<>();
    private final JSONObject details = new JSONObject();
    private Bundle arguments;
    private File ownedDirectory;
    private String currentCheck = "configuration";

    @Override public void onCreate(Bundle arguments) {
        super.onCreate(arguments);
        this.arguments = arguments == null ? new Bundle() : new Bundle(arguments);
        start();
    }

    @Override public void onStart() {
        long started = System.nanoTime();
        Throwable failure = null;
        try {
            runChecks();
        } catch (Throwable error) {
            failure = error;
        } finally {
            try {
                KadbCert.INSTANCE.clear();
                KadbCert.INSTANCE.configure(new InMemoryPrivateKeyStore(), new KadbCertPolicy(), Collections.emptyList());
                if (ownedDirectory != null && ownedDirectory.exists()) {
                    File[] files = ownedDirectory.listFiles();
                    require(files != null, "Cannot inspect owned identity directory during cleanup");
                    for (File file : files) require(file.isFile() && file.delete(), "Cannot remove owned identity file");
                    require(ownedDirectory.delete(), "Cannot remove owned identity directory");
                }
            } catch (Throwable cleanupError) {
                if (failure == null) failure = cleanupError;
                else if (failure != cleanupError) failure.addSuppressed(cleanupError);
            }
            for (byte[] copy : privateCopies) Arrays.fill(copy, (byte) 0);
        }
        Bundle result = new Bundle();
        try {
            JSONObject report = new JSONObject();
            report.put("schema", 1);
            report.put("status", failure == null ? "passed" : "failed");
            report.put("checks_executed", checks.size());
            report.put("checks", new JSONArray(checks));
            report.put("elapsed_ms", (System.nanoTime() - started) / 1_000_000);
            report.put("details", details);
            report.put("physical_device", false);
            report.put("device_kind", "android_emulator");
            if (failure != null) {
                report.put("failed_check", currentCheck);
                report.put("error_type", failure.getClass().getName());
                report.put("error", String.valueOf(failure.getMessage()));
                JSONArray frames = new JSONArray();
                for (StackTraceElement frame : failure.getStackTrace()) frames.put(frame.toString());
                report.put("stack_frames", frames);
            }
            result.putString("kadb_runtime_json", report.toString());
        } catch (Throwable reportError) {
            result.putString("kadb_runtime_reporting_error", reportError.getClass().getName());
            failure = reportError;
        }
        finish(failure == null ? Activity.RESULT_OK : Activity.RESULT_CANCELED, result);
    }

    private void runChecks() throws Exception {
        String host = arguments.getString("peer_host");
        String runId = arguments.getString("run_id");
        require("10.0.2.2".equals(host), "peer_host must explicitly name the emulator host alias 10.0.2.2");
        require(runId != null && runId.matches("[a-f0-9]{32}"), "run_id must be 32 lowercase hex characters");
        int port = Integer.parseInt(arguments.getString("peer_port", "0"));
        require(port > 0 && port <= 65535, "peer_port must be present and valid");
        require(Build.VERSION.SDK_INT >= 29, "This Android TLS 1.3 scenario requires API 29 or newer");
        require(Build.HARDWARE.contains("ranchu") || Build.HARDWARE.contains("goldfish"), "Expected emulator hardware");
        require("Dalvik".equals(System.getProperty("java.vm.name")), "Expected the Android runtime");
        require(!hasClass("org.conscrypt.OpenSSLProvider"), "APK must exercise Android's provider, not bundled host Conscrypt");
        details.put("sdk_int", Build.VERSION.SDK_INT);
        details.put("fingerprint", Build.FINGERPRINT);
        details.put("hardware", Build.HARDWARE);
        details.put("supported_abis", new JSONArray(Arrays.asList(Build.SUPPORTED_ABIS)));
        details.put("vm_name", System.getProperty("java.vm.name"));
        details.put("vm_version", System.getProperty("java.vm.version"));
        details.put("pid", Process.myPid());
        details.put("uid", Process.myUid());
        details.put("tls_provider", SSLContext.getInstance("TLSv1.3").getProvider().getName());
        details.put("bundled_conscrypt", false);
        details.put("peer_host", host);
        details.put("peer_port", port);

        ownedDirectory = new File(getTargetContext().getFilesDir(), "kadb-runtime-" + runId);
        require(!ownedDirectory.exists() && ownedDirectory.mkdir(), "Owned identity directory must be new");
        File keyFile = new File(ownedDirectory, "identity.pem");
        var policy = new KadbCertPolicy();
        var memory = new InMemoryPrivateKeyStore();
        KadbCert.INSTANCE.configure(memory, policy, Collections.emptyList());

        currentCheck = "identity_generate";
        KadbIdentitySnapshot original = remember(KadbCert.INSTANCE.ensureReady());
        X509Certificate certificate = certificate(original);
        require(((RSAPublicKey) certificate.getPublicKey()).getModulus().bitLength() == 2048, "Incorrect RSA size");
        certificate.checkValidity();
        certificate.verify(certificate.getPublicKey());
        require(certificate.getNotAfter().getTime() == original.getNotAfterEpochMillis(), "Certificate expiry differs from public snapshot");
        require(!original.getFingerprintSha256().isEmpty(), "Missing identity fingerprint");
        complete();

        currentCheck = "identity_export_copy_isolation";
        byte[] altered = remember(KadbCert.INSTANCE.exportPrivateKeyOrNull());
        require(Arrays.equals(altered, original.getPrivateKeyPem()), "Exported private key differs");
        Arrays.fill(altered, (byte) 0);
        byte[] exported = remember(KadbCert.INSTANCE.exportPrivateKeyOrNull());
        require(Arrays.equals(exported, original.getPrivateKeyPem()), "Caller changed Kadb's retained private key");
        complete();

        currentCheck = "identity_import_certificate";
        KadbIdentitySnapshot imported = remember(KadbCert.INSTANCE.importIdentity(original.getPrivateKeyPem(), original.getCertificatePem()));
        require(Arrays.equals(certificate(imported).getEncoded(), certificate.getEncoded()), "Valid imported certificate was not retained");
        require(imported.getFingerprintSha256().equals(original.getFingerprintSha256()), "Imported identity fingerprint changed");
        complete();

        currentCheck = "identity_file_persistence";
        var path = okio.Path.Companion.get(keyFile.getAbsolutePath(), false);
        KadbCert.INSTANCE.configure(new OkioFilePrivateKeyStore(path, FileSystem.SYSTEM), policy, Collections.emptyList());
        remember(KadbCert.INSTANCE.importPrivateKey(original.getPrivateKeyPem()));
        require(keyFile.isFile() && keyFile.length() > 0, "Private key was not persisted in app storage");
        KadbCert.INSTANCE.configure(new OkioFilePrivateKeyStore(path, FileSystem.SYSTEM), policy, Collections.emptyList());
        KadbIdentitySnapshot reloaded = remember(KadbCert.INSTANCE.ensureReady());
        require(Arrays.equals(reloaded.getPrivateKeyPem(), original.getPrivateKeyPem()), "Reloaded private key changed");
        require(Arrays.equals(certificate(reloaded).getPublicKey().getEncoded(), certificate.getPublicKey().getEncoded()), "Reloaded RSA identity changed");
        require(ownedDirectory.list().length == 1, "Unexpected staging file survived the completed write");
        complete();

        currentCheck = "identity_diagnostic_redaction";
        String diagnostic = reloaded.toString();
        require(!diagnostic.contains("privateKeyPem") && !diagnostic.contains("certificatePem")
                && !diagnostic.contains("PRIVATE KEY") && !diagnostic.contains("CERTIFICATE"), "Identity diagnostics expose PEM fields");
        require(diagnostic.contains(reloaded.getFingerprintSha256()), "Diagnostic fingerprint is missing");
        complete();

        currentCheck = "identity_parse_failure_retains_state";
        boolean parseRejected = false;
        try {
            remember(KadbCert.INSTANCE.importPrivateKey("not-a-private-key".getBytes(java.nio.charset.StandardCharsets.UTF_8)));
        } catch (KadbCertException.PrivateKeyParseFailed expected) {
            parseRejected = true;
        }
        require(parseRejected, "Invalid PEM did not use the public typed exception");
        KadbIdentitySnapshot retained = remember(KadbCert.INSTANCE.ensureReady());
        require(Arrays.equals(retained.getPrivateKeyPem(), original.getPrivateKeyPem()), "Failed import destroyed the ready identity");
        require(retained.getFingerprintSha256().equals(reloaded.getFingerprintSha256()), "Failed import replaced the ready certificate");
        complete();

        currentCheck = "pairing_positive";
        pair(host, port, "123456");
        complete();

        currentCheck = "pairing_wrong_code";
        boolean wrongCodeRejected = false;
        try {
            pair(host, port, "654321");
        } catch (IOException expected) {
            wrongCodeRejected = true;
        }
        require(wrongCodeRejected, "Wrong code was accepted");
        complete();

        currentCheck = "identity_clear";
        KadbCert.INSTANCE.clear();
        memory.clear();
        require(!keyFile.exists() && KadbCert.INSTANCE.exportPrivateKeyOrNull() == null, "Identity clear did not remove persisted state");
        complete();
    }

    private static void pair(String host, int port, String code) throws Exception {
        Function2<CoroutineScope, Continuation<? super Unit>, Object> action =
                (scope, continuation) -> Kadb.Companion.pair(host, port, code, "kadb-ios-interop", continuation);
        BuildersKt.<Unit>runBlocking(EmptyCoroutineContext.INSTANCE,
                (scope, continuation) -> TimeoutKt.withTimeout(20_000L, action, continuation));
    }

    private void complete() {
        checks.add(currentCheck);
        Bundle status = new Bundle();
        status.putString("stream", "PASS " + currentCheck + "\n");
        sendStatus(0, status);
    }

    private KadbIdentitySnapshot remember(KadbIdentitySnapshot snapshot) {
        require(snapshot != null, "Missing public identity snapshot");
        remember(snapshot.getPrivateKeyPem());
        return snapshot;
    }

    private byte[] remember(byte[] bytes) {
        require(bytes != null, "Missing private-key export");
        privateCopies.add(bytes);
        return bytes;
    }

    private static X509Certificate certificate(KadbIdentitySnapshot snapshot) throws Exception {
        return (X509Certificate) CertificateFactory.getInstance("X.509")
                .generateCertificate(new ByteArrayInputStream(snapshot.getCertificatePem()));
    }

    private static boolean hasClass(String name) {
        try { Class.forName(name); return true; }
        catch (ClassNotFoundException expected) { return false; }
    }

    private static void require(boolean condition, String message) {
        if (!condition) throw new IllegalStateException(message);
    }
}
