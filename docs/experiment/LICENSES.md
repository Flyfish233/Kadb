# Experimental combination: license and distribution boundaries

## Sources retain their own licenses

| Component | Exact source | License / notice |
| --- | --- | --- |
| Existing Kadb code | Upstream baseline `75678915fd4bdd52345edbb6bc4913ae3415a680` | Apache-2.0, existing root `LICENSE` and file headers retained |
| New Legacy SPAKE25519 runtime and required primitives | `Flyfish233/spake2@b837aba27bebc1050965fa124c2efa54b4e4544a` | AGPL-3.0-only, no linking exception; full license at `third-party/spake2/upstream/LICENSE` |
| Kadb-owned integration and build adaptation | This experiment's commits | Apache-2.0 at the source-file level; distribution of a combined program remains subject to the AGPL component's requirements |
| Historical test fixture data | `Flyfish233/spake2-java@809ad7aa731f475c07763b1ad2c165ae192dfb5f`, via pinned SPAKE2 | GPLv3, complete original license under `validation/spake2/`; test-only |
| Native TLS, RSA/X.509, HKDF and AES provider | Pinned BoringSSL recorded by the Native backend | Its original composite license and third-party notices remain required; see Native provenance |

The experiment does not replace the root Apache license or claim a power to
relicense other authors' original Kadb source as AGPL. The new SPAKE2 dependency
is not an Apache-only artifact. There is no exception allowing the combined
runtime to be advertised or distributed under Apache-2.0 alone.

## Consequences for a combined program

Kadb links the AGPL Legacy module directly into its runtime; Native frameworks
may statically incorporate it. A binary/source distribution of that combined
covered work must satisfy the applicable AGPL-3.0 terms, including preserving
license/copyright notices and providing the complete Corresponding Source by an
appropriate section-6 method. An upstream URL or a hash alone is not a substitute
for the source offer required for a particular binary conveyance.

For this build, Corresponding Source includes the actual pinned runtime sources,
the integration modifications, and scripts/configuration needed to build the
covered work. Third-party components keep their original notices. A downstream
application that incorporates this runtime must evaluate and satisfy the same
combination obligations; separating it into a Maven module or `.klib` does not
by itself create a linking exception.

AGPL section 13 also addresses modified versions that support remote network
interaction: those users must be offered the Corresponding Source through the
specified network mechanism. Merely running an unmodified dependency locally is
not equivalent to a general obligation to publish all private work to everyone.
The exact distribution or network deployment determines the applicable duties.

This repository records an experiment and its source. No Maven Central release,
formal JitPack version/tag, GitHub Release, final distribution policy or App Store
delivery is authorized by this work. CI build/test artifacts are experimental and
must retain source provenance and this licensing context.

## Primary texts

- AGPL-3.0 full text (sections 1, 4–6 and 13):
  <https://www.gnu.org/licenses/agpl-3.0.html>, with the complete text retained in
  `third-party/spake2/upstream/LICENSE`.
- Apache Software Foundation's explanation of GPLv3 compatibility and retention
  of Apache source conditions: <https://www.apache.org/licenses/GPL-compatibility.html>.
- GNU licensing FAQ, including combined-work and AGPL Corresponding Source:
  <https://www.gnu.org/licenses/gpl-faq.html>.
