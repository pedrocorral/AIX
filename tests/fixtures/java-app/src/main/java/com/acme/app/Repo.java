package com.acme.app;
import java.sql.*;
public class Repo {
    public String find(int id) throws Exception {
        String q = "SELECT * FROM t WHERE id = " + id;
        return DriverManager.getConnection("jdbc:x").createStatement().executeQuery(q).getString(1);
    }
}
