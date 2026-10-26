package com.flyfishxu.kadb.cert

data class KadbIdentitySnapshot(
    val privateKeyPem: ByteArray,
    val certificatePem: ByteArray,
    val fingerprintSha256: String,
    val notAfterEpochMillis: Long
) {
    // Diagnostics must not serialize PEM fields, including in failed assertions.
    override fun toString(): String =
        "KadbIdentitySnapshot(fingerprintSha256=$fingerprintSha256, notAfterEpochMillis=$notAfterEpochMillis)"

    internal fun deepCopy(): KadbIdentitySnapshot {
        return copy(
            privateKeyPem = privateKeyPem.copyOf(),
            certificatePem = certificatePem.copyOf()
        )
    }
}
