# Module 3: CSVTable Implementation

## CSVTable.java

### Overview

`CSVTable` is a file-backed table that persists data to a CSV file in `db/tables/<name>.csv`.
It implements `FileTable` (extending `Table`, `Flushable`, `AutoCloseable`), `QueryTable`, and
`PrettyTable`. All table operations are delegated to an in-memory `HashTable`; every mutation
is immediately flushed to disk so the file is always consistent.

### Design Decisions

**Backing Store**

An internal `HashTable` (`inMemory`) serves as the in-memory layer. This gives O(1) average-case
put/get/remove and reuses the fingerprint (hashCode) logic already validated in Module 2.
Only two instance fields are needed:

| Field      | Type           | Description |
|------------|----------------|-------------|
| `csvFile`  | `final Path`   | Path to `db/tables/<name>.csv` |
| `inMemory` | `final HashTable` | In-memory delegate for all table operations |

Both types are allowed by the Module 3 forbidden-class exemptions (`java.nio.file.Path` and
the `tables` package).

**File Format**

```
col1,col2,col3,...          ← header: comma-separated column names
key1,S:str,I:42,B:true,N:  ← data row: key (unencoded), then type-tagged values
key2,N:,I:-7,B:false,S:hi
```

Type encoding for value cells:

| Prefix  | Java type   | Example encoded |
|---------|-------------|-----------------|
| `S:`    | `String`    | `S:hello`       |
| `I:`    | `Integer`   | `I:42`          |
| `B:`    | `Boolean`   | `B:true`        |
| `N:`    | `null`      | `N:`            |

Type tags allow exact round-trip reconstruction of all four value types that the test harness
produces, preserving `hashCode()` compatibility with the control table.

**Constructors**

- `CSVTable(String newName, List<String> newColumns)` — Creates a fresh `HashTable` and writes
  the CSV header. Any pre-existing file with the same name is overwritten.
- `CSVTable(String existingName)` — Reads the CSV header to reconstruct columns, then puts
  each data row into a fresh `HashTable`. After this constructor the fingerprint equals that
  of the table state that was last flushed.

**Flush Strategy**

`flush()` rewrites the entire CSV (header + all live rows from the `HashTable` iterator).
It is called after every mutation:

- `put(key, values)` — always flushes (whether hit or miss)
- `remove(key)` — flushes only on a hit (non-null return)
- `clear()` — flushes (leaves only the header line)

If `put` throws `IllegalArgumentException` (wrong values size), the exception propagates
before `flush()` is called, so the file is not modified.

**Fingerprint**

`hashCode()` delegates to `inMemory.hashCode()`, which maintains a running fingerprint using
`Row(key, values).hashCode()` (Java record hash). This matches the `ControlRow` fingerprint
in the test harness because both records have identical component types and use the same
JVM record hash implementation.

When reopening from CSV, each row is inserted into a fresh `HashTable` via `put` (all misses),
rebuilding the fingerprint incrementally. Type preservation ensures the fingerprint matches.

**Null values**

`null` table values are supported. The `Collections.unmodifiableList` wrapper (instead of
`List.copyOf`) is used when reconstructing value lists from CSV, since `List.copyOf` rejects
null elements.

### Methods

| Method | Description |
|--------|-------------|
| `CSVTable(name, columns)` | Create new table; write header to disk |
| `CSVTable(name)` | Open existing table; parse CSV and populate HashTable |
| `flush()` | Rewrite entire CSV from in-memory state |
| `clear()` | Delegate to HashTable, then flush |
| `put(key, values)` | Delegate to HashTable (may throw IAE), then flush |
| `get(key)` | Delegate to HashTable; no flush |
| `remove(key)` | Delegate to HashTable; flush only on hit |
| `degree()` | Delegates to `inMemory.degree()` |
| `size()` | Delegates to `inMemory.size()` |
| `hashCode()` | Delegates to `inMemory.hashCode()` (fingerprint) |
| `equals(obj)` | `obj instanceof Table && hashCode() == obj.hashCode()` |
| `iterator()` | Delegates to `inMemory.iterator()` |
| `name()` | Delegates to `inMemory.name()` |
| `columns()` | Delegates to `inMemory.columns()` |
| `toString()` | Calls `toPrettyString()` from `PrettyTable` |

---

## Sandbox.java

The Sandbox demonstrates three `CSVTable` scenarios:

1. **Video Games** — Creates a new table, inserts 5 rows, performs a get (hit and miss), an
   update put (returns old values), and a remove. Then reopens the same CSV with the
   1-parameter constructor and confirms name, columns, size, and fingerprint match.

2. **Programming Languages** — Creates a table, inserts 4 rows, iterates with a for-each loop,
   calls `clear()`, then reopens to confirm the cleared state persisted.

3. **Type Preservation** — Creates a table with String, Integer, Boolean, and null values.
   Reopens it and verifies each value's Java type was restored correctly and the fingerprint
   matches the original.
