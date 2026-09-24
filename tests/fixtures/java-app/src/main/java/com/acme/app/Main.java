package com.acme.app;
import com.acme.util.*;
public class Main {
    public static void main(String[] args) {
        Service s = new Service();
        System.out.println(s.run(Text.upper("x")));
    }
}
