package com.flyfishxu.kadb.cert

import kotlin.io.encoding.Base64
import kotlin.test.Test
import kotlin.test.assertFalse
import kotlin.test.assertTrue

class IdentityDiagnosticRedactionTest {
    private val syntheticPrivate = "SYNTHETIC_ONLY_PRIVATE_MATERIAL".encodeToByteArray()
    private val syntheticCertificate = "SYNTHETIC_ONLY_CERTIFICATE".encodeToByteArray()

    private fun snapshot() = KadbIdentitySnapshot(
        privateKeyPem = syntheticPrivate,
        certificatePem = syntheticCertificate,
        fingerprintSha256 = "synthetic-public-fingerprint",
        notAfterEpochMillis = 1234L
    )

    @Test fun publicSnapshotDiagnosticsOmitPrivateMaterial() {
        assertSafeDiagnostic(snapshot().toString(), "KadbIdentitySnapshot")
    }

    @Test fun internalIdentityDiagnosticsOmitPrivateMaterial() {
        // Reuse a committed public fixture solely to obtain a platform key-pair
        // object. The aggregate under test contains only synthetic secret bytes.
        val keyPair = CertUtils.identityFromPrivateKeyAndCertificate(
            Base64.decode(JvmIdentityFixture.privatePem),
            Base64.decode(JvmIdentityFixture.certificatePem)
        ).keyPair
        val identity = ResolvedIdentity(syntheticPrivate, keyPair, snapshot())
        assertSafeDiagnostic(identity.toString(), "ResolvedIdentity")
    }

    private fun assertSafeDiagnostic(text: String, type: String) {
        // Failure messages deliberately never interpolate the rendered identity.
        assertFalse(text.contains("privateKeyPem"), "Diagnostic must omit the private-key field")
        assertFalse(text.contains(syntheticPrivate.contentToString()), "Diagnostic must omit private-key bytes")
        assertFalse(text.contains(syntheticCertificate.contentToString()), "Diagnostic must omit certificate bytes")
        assertTrue(text.startsWith(type), "Diagnostic should identify its type")
        assertTrue(text.contains("synthetic-public-fingerprint"), "Diagnostic should retain the public fingerprint")
    }
}
