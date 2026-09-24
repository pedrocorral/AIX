package com.acme.app;
import org.junit.jupiter.api.Test;
public class ServiceTest {
    @Test
    void runsWithNull() { new Service().run(null); }
}
