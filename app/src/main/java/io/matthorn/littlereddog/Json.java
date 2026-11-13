package io.matthorn.littlereddog;

import java.util.ArrayList;
import java.util.LinkedHashMap;

/**
 * A small JSON reader for the art files: objects become LinkedHashMap&lt;String, Object&gt;, arrays ArrayList&lt;Object&gt;,
 * numbers Long (no fraction or exponent) or Double, strings String, and true, false, null as Boolean and null.
 */
public final class Json {

    private final String s;
    private int at;

    private Json(String s) {
        this.s = s;
    }

    public static Object parse(String text) {
        Json j = new Json(text);
        Object v = j.value();
        j.space();
        if (j.at != j.s.length()) throw j.error("text after the value");
        return v;
    }

    private IllegalArgumentException error(String what) {
        return new IllegalArgumentException("JSON: " + what + " at character " + at);
    }

    private void space() {
        while (at < s.length() && " \t\r\n".indexOf(s.charAt(at)) >= 0) at++;
    }

    private Object value() {
        space();
        if (at >= s.length()) throw error("end of text");
        char c = s.charAt(at);
        if (c == '{') return object();
        if (c == '[') return array();
        if (c == '"') return string();
        if (s.startsWith("true", at)) {
            at += 4;
            return Boolean.TRUE;
        }
        if (s.startsWith("false", at)) {
            at += 5;
            return Boolean.FALSE;
        }
        if (s.startsWith("null", at)) {
            at += 4;
            return null;
        }
        return number();
    }

    private LinkedHashMap<String, Object> object() {
        LinkedHashMap<String, Object> out = new LinkedHashMap<>();
        at++;
        space();
        if (s.charAt(at) == '}') {
            at++;
            return out;
        }
        while (true) {
            space();
            if (s.charAt(at) != '"') throw error("a key");
            String key = string();
            space();
            if (s.charAt(at++) != ':') throw error("':'");
            out.put(key, value());
            space();
            char c = s.charAt(at++);
            if (c == '}') return out;
            if (c != ',') throw error("',' or '}'");
        }
    }

    private ArrayList<Object> array() {
        ArrayList<Object> out = new ArrayList<>();
        at++;
        space();
        if (s.charAt(at) == ']') {
            at++;
            return out;
        }
        while (true) {
            out.add(value());
            space();
            char c = s.charAt(at++);
            if (c == ']') return out;
            if (c != ',') throw error("',' or ']'");
        }
    }

    private String string() {
        StringBuilder b = new StringBuilder();
        at++;
        while (true) {
            if (at >= s.length()) throw error("an unclosed string");
            char c = s.charAt(at++);
            if (c == '"') return b.toString();
            if (c != '\\') {
                b.append(c);
                continue;
            }
            char e = s.charAt(at++);
            switch (e) {
                case '"': case '\\': case '/': b.append(e); break;
                case 'b': b.append('\b'); break;
                case 'f': b.append('\f'); break;
                case 'n': b.append('\n'); break;
                case 'r': b.append('\r'); break;
                case 't': b.append('\t'); break;
                case 'u':
                    b.append((char) Integer.parseInt(s.substring(at, at + 4), 16));
                    at += 4;
                    break;
                default: throw error("an unknown escape \\" + e);
            }
        }
    }

    private Object number() {
        int start = at;
        boolean whole = true;
        while (at < s.length() && "+-0123456789.eE".indexOf(s.charAt(at)) >= 0) {
            if (".eE".indexOf(s.charAt(at)) >= 0) whole = false;
            at++;
        }
        if (start == at) throw error("a value");
        String t = s.substring(start, at);
        return whole ? (Object) Long.parseLong(t) : (Object) Double.parseDouble(t);
    }
}
