package com.acme.app;
public class Service {
    private final Repo repo = new Repo();
    public String run(String v) {
        if (v == null) { return ""; }
        switch (v) { case "a": return repo.find(1); default: break; }
        return repo.find(2);
    }
}
