# Deep modules (after Ousterhout, *A Philosophy of Software Design*)
- Depth = functionality / interface size. Shallow = an interface as big as its implementation (a class per method).
- Information hiding: a design decision known by one module only. Leakage = the same decision known by two.
- Pull complexity downward: the module does the hard part so every caller does not.
- Define errors out of existence: an API that cannot be misused beats one that reports misuse.
- Design it twice: two sketches, compare, choose. Cheap now, expensive later.
- General-purpose interfaces with special-purpose implementations tend to be deeper.
