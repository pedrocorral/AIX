"""Spring Security and Java platform rules (securityrules.py, infrarules.spring): CSRF and headers disabled in the
three Spring syntaxes, CORS open to every origin, H2 console and stack traces exposed, a signing key in the code,
a trust-all TLS manager, an XML parser without external entities disabled in its method, Basic auth without
requiresSecure(), anyRequest().permitAll(); each with a correct counterpart that stays quiet."""
import re, unittest

from helpers import install, project_cmd, temp_home

SAMPLES = {
    "src/main/java/com/a/SecurityConfig.java": """package com.a;
@Configuration
public class SecurityConfig {
  SecurityFilterChain api(HttpSecurity http) throws Exception {
    http.csrf(csrf -> csrf.disable());
    http.csrf(AbstractHttpConfigurer::disable);
    http.csrf().disable();
    http.headers(headers -> headers.disable());
    http.httpBasic(Customizer.withDefaults());
    http.authorizeHttpRequests(a -> a.anyRequest().permitAll());
    return http.build();
  }
  SecurityFilterChain safe(HttpSecurity http) throws Exception {
    http.csrf(csrf -> csrf.ignoringRequestMatchers("/api/webhook"));
    http.headers(h -> h.frameOptions(f -> f.sameOrigin()));
    http.requiresChannel(c -> c.anyRequest().requiresSecure());
    http.authorizeHttpRequests(a -> a.requestMatchers("/public/**").permitAll().anyRequest().authenticated());
    return http.build();
  }
}
""",
    "src/main/java/com/a/Api.java": """package com.a;
@CrossOrigin("*")
@RestController
public class Api {
  @CrossOrigin(origins = "https://app.example.com")
  public String ok() { return ""; }
  public void cors(CorsConfiguration c) { c.addAllowedOrigin("*"); c.setAllowedOrigins(List.of("https://app.example.com")); }
  public String token(String subject) {
    return Jwts.builder().setSubject(subject).signWith(SignatureAlgorithm.HS256, "my-super-secret-signing-key").compact();
  }
  public String tokenFromEnv(String subject) {
    return Jwts.builder().setSubject(subject).signWith(SignatureAlgorithm.HS256, System.getenv("JWT_KEY")).compact();
  }
  public void trust() throws Exception {
    TrustManager[] all = new TrustManager[] { new X509TrustManager() {
      public void checkServerTrusted(X509Certificate[] c, String a) { }
      public X509Certificate[] getAcceptedIssuers() { return null; }
    }};
    HttpsURLConnection.setDefaultHostnameVerifier((host, session) -> true);
  }
}
""",
    "src/main/java/com/a/Xml.java": """package com.a;
public class Xml {
  public Document unsafe(InputStream in) throws Exception {
    DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
    return dbf.newDocumentBuilder().parse(in);
  }
  public Document safe(InputStream in) throws Exception {
    DocumentBuilderFactory dbf = DocumentBuilderFactory.newInstance();
    dbf.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
    return dbf.newDocumentBuilder().parse(in);
  }
  public XMLStreamReader stax(Reader r) throws Exception {
    XMLInputFactory xif = XMLInputFactory.newInstance();
    xif.setProperty(XMLConstants.ACCESS_EXTERNAL_DTD, "");
    return xif.createXMLStreamReader(r);
  }
}
""",
    "src/main/resources/application.properties": "spring.h2.console.enabled=true\nserver.error.include-stacktrace=always\nspring.datasource.url=jdbc:h2:mem:test\n",
    "src/main/resources/application-prod.yml": "server:\n  error:\n    include-stacktrace: never\n",
}


class SpringRules(unittest.TestCase):
    def setUp(self):
        self.home = temp_home(self); self.project = self.home / "app"
        for name, src in SAMPLES.items():
            (self.project / name).parent.mkdir(parents=True, exist_ok=True)
            (self.project / name).write_text(src, encoding="utf-8")
        install(self.home, self.project)
        self.out = project_cmd(self.project, self.home, "code", "security", "src", check=False).stdout

    def lines(self, file: str) -> list:
        return sorted((int(m.group(1)), m.group(2)) for m in re.finditer(rf"{re.escape(file)}:(\d+)  (.+?) \(CWE-\d+\)", self.out))

    def test_security_configuration(self):
        self.assertEqual(self.lines("SecurityConfig.java"), [(5, "CSRF protection disabled (Spring Security)"), (6, "CSRF protection disabled (Spring Security)"), (7, "CSRF protection disabled (Spring Security)"),
                                                            (8, "security headers disabled (Spring Security)"), (9, "HTTP Basic authentication without requiresSecure()"), (10, "every request permitted (anyRequest().permitAll())")], self.out)

    def test_cors_keys_and_trust(self):
        self.assertEqual(self.lines("Api.java"), [(2, "CORS open to every origin"), (7, "CORS open to every origin"), (9, "signing key written in the code (JWT / HMAC)"),
                                                 (16, "TLS trust disabled (trust-all manager or verifier)"), (17, "TLS trust disabled (trust-all manager or verifier)"), (19, "TLS trust disabled (trust-all manager or verifier)")], self.out)

    def test_xxe_scoped_to_the_method(self):
        self.assertEqual(self.lines("Xml.java"), [(4, "XML parser without external entities disabled (XXE)")], self.out)

    def test_properties(self):
        self.assertEqual(self.lines("application.properties"), [(1, "development console or stack traces exposed"), (2, "development console or stack traces exposed")], self.out)
        self.assertEqual(self.lines("application-prod.yml"), [], self.out)


if __name__ == "__main__":
    unittest.main()
