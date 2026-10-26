package com.flyfishxu.kadb.cert

import kotlin.io.encoding.Base64
import kotlin.test.Test
import kotlin.test.assertFailsWith

class CertificateSubjectNativeTest {
    @Test fun invalidCountryUsesTheCertificatePolicyExceptionBoundary() {
        val privatePem = Base64.decode(JvmIdentityFixture.privatePem)
        try {
            assertFailsWith<KadbCertException.PolicyViolation> {
                CertUtils.identityFromPrivateKey(privatePem,
                    KadbCertPolicy(subject = KadbCertPolicy.Subject(c = "USA")))
            }
        } finally {
            privatePem.fill(0)
        }
    }

    @Test fun embeddedNulCannotCreateATruncatedNativeIdentity() {
        val subjects = listOf(
            KadbCertPolicy.Subject(cn = "Adb\u0000different"),
            KadbCertPolicy.Subject(ou = "unit\u0000different"),
            KadbCertPolicy.Subject(o = "Android\u0000different"),
            KadbCertPolicy.Subject(l = "city\u0000different"),
            KadbCertPolicy.Subject(st = "region\u0000different"),
            KadbCertPolicy.Subject(c = "US\u0000GB")
        )
        val privatePem = Base64.decode(JvmIdentityFixture.privatePem)
        try {
            subjects.forEach { subject ->
                assertFailsWith<KadbCertException.PolicyViolation> {
                    CertUtils.identityFromPrivateKey(privatePem, KadbCertPolicy(subject = subject))
                }
            }
        } finally {
            privatePem.fill(0)
        }
    }
}
