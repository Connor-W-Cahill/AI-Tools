# Module 3: CSVTable Implementation

## CSVTable.java

### Overview

`CSVTable` is a pure file-backed table that persists all data to a CSV file at
`db/tables/<name>.csv`. It implements `FileTable` (extending `Table`, `Flushable`,
`AutoCloseable`), `QueryTable`, and `PrettyTable`. There is no in-memory data structure —
every operation reads from or writes to the file directly.

### Fields

| Field      | Type         | Description |
|------------|--------------|-------------|
| `BASE_DIR` | `static final Path` | Base directory `db/tables/` |
| `csvFile`  | `final Path` | Path to `db/tables/<name>.csv` |

Only `Path` fields are used, satisfying the Module 3 forbidden-class restrictions.

### File Format

```
"title","genre","year","solo"          ← header: quoted column names
"Minecraft","sandbox",2011,true        ← data row: quoted key, then encoded values
"Hades","roguelike",2018,true
"Valheim","survival",2021,false
```

Encoding rules for value cells:

| Java type   | Encoding          | Example       |
|-------------|-------------------|---------------|
| `String`    | double-quoted     | `"hello"`     |
| `Integer`   | plain number      | `42`          |
| `Boolean`   | plain true/false  | `true`        |
| `null`      | empty field       | *(nothing)*   |

Keys are always strings and are always double-quoted. Column names in the header are
also double-quoted. This allows exact round-trip reconstruction of all four value types,
preserving `hashCode()` compatibility with the control table.

### Constructors

- `CSVTable(String newName, List<String> newColumns)` — Creates `db/tables/` if needed,
  then writes the header line to a new file. Any pre-existing file is overwritten.
- `CSVTable(String existingName)` — Guards that both `db/tables/` and
  `<existingName>.csv` exist, then accepts the path. All data is read from the file
  on demand.

### Properties (no amortization)

Each property reads directly from the file on every call:

- `name()` — derived from the filename by stripping `.csv`
- `columns()` — reads and decodes the header line
- `degree()` — returns `columns().size()`
- `size()` — reads all lines and counts non-empty data rows
- `hashCode()` — reads all data rows, decodes each to a `Row`, sums `Row.hashCode()`

### Standard Operations

| Method | Behavior |
|--------|----------|
| `clear()` | Reads columns, then rewrites the file with only the header line |
| `put(key, values)` | Guards null/empty key and wrong values size. Scans file for key: on hit rewrites the file with the updated row; on miss appends the new row. Returns old values or null. |
| `get(key)` | Guards null/empty key. Scans file and returns values on hit, null on miss. No write. |
| `remove(key)` | Guards null/empty key. Scans file: on hit removes the row and rewrites; on miss returns null without writing. |
| `iterator()` | Reads all data rows into a `List<Row>`, returns `list.iterator()`. No `hasNext`/`next` implemented. |

### Encoding Helpers

| Method | Description |
|--------|-------------|
| `encodeFields(List<String>)` | Joins strings with commas, each wrapped in double quotes. Used for the header line. |
| `decodeFields(String)` | Splits on commas and strips double quotes. Used to read the header. |
| `encodeRow(String, List<Object>)` | Encodes a data row: quoted key, then each value by type. |
| `decodeRow(String)` | Decodes a data row: strips quotes from key, infers type of each value field. |
| `encodeField(Object)` | Quotes strings, writes integers/booleans as-is, empty string for null. |
| `decodeField(String)` | Empty → null; quoted → String; `true`/`false` → Boolean; otherwise → Integer. |

---

# Module 4: JSONTable Implementation

## JSONTable.java

### Overview

`JSONTable` is a file-backed table that persists all data to a JSON file at
`db/tables/<name>.json`. It implements `FileTable`, `QueryTable`, and `PrettyTable`.
All state is stored in an in-memory `ObjectNode` (`tree`) that is written to disk on
every mutating operation via `flush()`.

### Fields

| Field      | Type                  | Description |
|------------|-----------------------|-------------|
| `baseDir`  | `static final Path`   | Base directory `db/tables/` |
| `jsonFile` | `final Path`          | Path to `db/tables/<name>.json` |
| `helper`   | `static final ObjectMapper` | Shared Jackson mapper for reading/writing JSON |
| `tree`     | `final ObjectNode`    | In-memory root node; mirrors the JSON file at all times |

Only `Path`, `ObjectMapper`, and `ObjectNode` fields are used, satisfying the Module 4
forbidden-class restrictions.

### File Format

```json
{
  "name": "tableName",
  "columns": ["k1", "f1a", "f1b"],
  "rows": {
    "key1": ["hello", 42, true],
    "key2": ["world", null, false]
  }
}
```

The `rows` object maps each key (always a string) to a JSON array of values. Value
types map directly to JSON primitives:

| Java type   | JSON encoding   | Example        |
|-------------|-----------------|----------------|
| `String`    | JSON string     | `"hello"`      |
| `Integer`   | JSON number     | `42`           |
| `Boolean`   | JSON boolean    | `true`         |
| `null`      | JSON null       | `null`         |

This allows exact round-trip reconstruction of all four value types, preserving
`hashCode()` compatibility with the control table.

### Constructors

- `JSONTable(String newName, List<String> newColumns)` — Creates `db/tables/` if needed,
  initializes a fresh `ObjectNode` with `name`, `columns`, and an empty `rows` object,
  then calls `flush()` to write it to disk.
- `JSONTable(String existingName)` — Guards that the `.json` file exists, then reads it
  back from disk into `tree` via `helper.readTree()`. All subsequent operations work
  against the in-memory `tree`.

### Properties

Each property reads directly from `tree` (no file I/O after construction):

- `name()` — returns `tree.get("name").textValue()`
- `columns()` — iterates the `columns` array node, returns an unmodifiable list
- `degree()` — returns `columns().size()`
- `size()` — returns `tree.get("rows").size()`
- `hashCode()` — iterates all entries in the `rows` object, decodes each to a `Row`,
  sums `Row.hashCode()` (matching the control table fingerprint algorithm)

### Standard Operations

| Method | Behavior |
|--------|----------|
| `clear()` | Calls `removeAll()` on the `rows` ObjectNode, then flushes to disk |
| `put(key, values)` | Guards wrong values size. Checks `rows` for an existing entry: on hit saves old decoded values, replaces the array, flushes, returns old; on miss adds new array, flushes, returns null |
| `get(key)` | Looks up key in `rows`; returns decoded values on hit, null on miss. No flush. |
| `remove(key)` | Looks up key in `rows`; on hit decodes old values, removes the entry, flushes, returns old; on miss returns null |
| `iterator()` | Iterates `rows.properties()`, decodes each entry into a `Row`, returns a list iterator |

### Encoding Helpers

| Method | Description |
|--------|-------------|
| `encodeValue(ArrayNode, Object)` | Appends one typed value to a Jackson `ArrayNode`: null → `addNull()`, String → `add(s)`, Integer → `add(i)`, Boolean → `add(b)` |
| `decodeValues(JsonNode)` | Iterates a value array node; maps `isNull` → null, `isTextual` → String, `isInt` → Integer, `isBoolean` → Boolean |

---

## QueryTable.java (Module 4 additions)

Three set-algebra query methods are implemented as default methods in the `QueryTable`
interface. All return a new `HashTable` result; the source tables are not modified.

### union(QueryTable table)

Returns a new table containing all rows from `this` plus any rows from `table` whose
key does not already exist in `this`. Rows from `this` take precedence on key conflicts.

**Algorithm:**
1. Create a new `HashTable` named `<name>_union` with the same columns
2. Put all rows from `this` into the result
3. For each row in `table`, put it only if the key is not already in the result

### intersect(QueryTable table)

Returns a new table containing only the rows of `this` whose key also appears in `table`.

**Algorithm:**
1. Create a new `HashTable` named `<name>_intersect` with the same columns
2. For each row in `this`, add it to the result only if `table.contains(row.key())`

### minus(QueryTable table)

Returns a new table containing only the rows of `this` whose key does **not** appear
in `table`.

**Algorithm:**
1. Create a new `HashTable` named `<name>_minus` with the same columns
2. For each row in `this`, add it to the result only if `!table.contains(row.key())`

---

## QueryTable.java

`select` is implemented as a default method directly in the `QueryTable` interface, as
required by the rubric ("In the Query Table API only").

### select(String column, Object criteria)

Returns a new `HashTable` containing only the rows where the value in `column` equals
`criteria`. The result has the same columns as the original table.

**Algorithm:**
1. Get column list and find the index of `column`
2. Create a new `HashTable` with the same name (suffixed `_select`) and columns
3. Iterate over `this` — for each row, retrieve the value at `idx` (key if `idx == 0`,
   otherwise `values.get(idx - 1)`)
4. If the value equals `criteria` (null-safe), put the row into the result table
5. Return the result

Supports matching on String, Integer, Boolean, and null criteria.

---

## Sandbox.java

The Sandbox demonstrates three original `CSVTable` instances, covering all constructors,
properties, standard operations, and the `select` query method.

### 1. Video Games (`csv_games`)

- Creates a new table with 7 rows
- Demonstrates `degree()`, `size()`, iterator (for-each)
- `put` hit — returns old values; confirms new value updated
- `put` miss — returns null
- `remove` hit and miss
- Reopens with 1-parameter constructor; verifies `name`, `columns`, `size`, and
  fingerprint (`hashCode`) match across the disk round-trip

### 2. Albums (`csv_albums`)

- Creates a new table with 7 rows
- `select` on a String column: `artist = "Kendrick"` → 2 results
- `select` on an Integer column: `year = 1973` → 1 result
- `select` on a Boolean column: `explicit = true` → 2 results
- `select` with no matches: `artist = "Drake"` → 0 results
- `clear()`, then reopens to confirm the cleared state persisted to disk

### 3. Planets (`csv_planets`)


- Creates a new table with 8 rows containing String, Integer, Boolean, and null values
- `select` on a String column: `type = "gas giant"` → 2 results
- `select` on a null criteria: `life = null` → 2 results (Mercury, Venus)
- Reopens with 1-parameter constructor; verifies each field's Java type was preserved
  correctly after the disk round-trip
- Confirms fingerprints match between original and reopened table

### 4. Albums (`json_albums`)

- Creates a new `JSONTable` with 7 rows (String, Integer, Boolean values)
- Demonstrates `degree()`, `size()`, iterator (for-each)
- `put` hit — returns old artist string; confirms new value updated
- `put` miss — returns null for unknown key
- `remove` hit and miss
- Reopens with 1-parameter constructor; verifies `name`, `columns`, `size`, and
  fingerprint (`hashCode`) match across the disk round-trip

### 5. Rock Albums (`json_rock_albums`)

- Creates a new `JSONTable` with 4 rows using the same schema as `json_albums`
- Reopens and verifies fingerprint survives round-trip
- Serves as the right-hand operand for `intersect` and `minus`

### 6. Hip-Hop Albums (`json_hiphop_albums`)

- Creates a new `JSONTable` with 4 rows using the same schema as `json_albums`
- Includes two keys that overlap with `json_albums` (Kendrick entries)
- Reopens and verifies fingerprint survives round-trip
- Serves as the right-hand operand for `union`
- **`union`** with `json_albums`: all 9 unique albums (overlapping Kendrick keys kept from `json_albums`)
- **`intersect`** with `json_rock_albums`: rows in `json_albums` whose key also exists in `json_rock_albums`
- **`minus`** with `json_rock_albums`: rows in `json_albums` not present in `json_rock_albums`
