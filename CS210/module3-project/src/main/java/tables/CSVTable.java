package tables;

import java.io.IOException;
import java.io.PrintWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;

import features.FileTable;
import features.PrettyTable;
import features.QueryTable;
import features.Table;

public class CSVTable implements FileTable, QueryTable, PrettyTable {
	private static final Path BASE_DIR = Paths.get("db", "tables");

	private final Path csvFile;
	private final HashTable inMemory;

	/**
	 * Creates a new CSV-backed table (overwrites any existing file).
	 *
	 * @param newName    table name; also used as the CSV filename (without extension)
	 * @param newColumns ordered column names; the first column is the key column
	 */
	public CSVTable(String newName, List<String> newColumns) {
		csvFile = BASE_DIR.resolve(newName + ".csv");
		inMemory = new HashTable(newName, newColumns);
		try {
			Files.createDirectories(BASE_DIR);
			writeHeader();
		}
		catch (IOException e) {
			throw new RuntimeException("Failed to create CSV table: " + newName, e);
		}
	}

	/**
	 * Opens an existing CSV-backed table and loads its data into memory.
	 *
	 * @param existingName table name; the file {@code db/tables/<existingName>.csv} must exist
	 */
	public CSVTable(String existingName) {
		csvFile = BASE_DIR.resolve(existingName + ".csv");
		try {
			List<String> lines = Files.readAllLines(csvFile);
			List<String> columns = Arrays.asList(lines.get(0).split(",", -1));
			inMemory = new HashTable(existingName, columns);
			for (int i = 1; i < lines.size(); i++) {
				String line = lines.get(i);
				if (line.isEmpty()) continue;
				String[] parts = line.split(",", -1);
				String key = parts[0];
				List<Object> values = new ArrayList<>(parts.length - 1);
				for (int j = 1; j < parts.length; j++) {
					values.add(decodeValue(parts[j]));
				}
				inMemory.put(key, Collections.unmodifiableList(values));
			}
		}
		catch (IOException e) {
			throw new RuntimeException("Failed to open CSV table: " + existingName, e);
		}
	}

	// -------------------------------------------------------------------------
	// FileTable: flush / close
	// -------------------------------------------------------------------------

	@Override
	public void flush() {
		try {
			Files.createDirectories(BASE_DIR);
			try (PrintWriter pw = new PrintWriter(Files.newBufferedWriter(csvFile))) {
				pw.println(String.join(",", inMemory.columns()));
				for (Row row : inMemory) {
					StringBuilder sb = new StringBuilder(row.key());
					for (Object v : row.values()) {
						sb.append(',').append(encodeValue(v));
					}
					pw.println(sb.toString());
				}
			}
		}
		catch (IOException e) {
			throw new RuntimeException("Failed to flush CSV table", e);
		}
	}

	// -------------------------------------------------------------------------
	// Encoding helpers (type-tagged CSV cells)
	// Format:  N:       -> null
	//          I:<n>    -> Integer n
	//          B:<bool> -> Boolean
	//          S:<str>  -> String str
	// -------------------------------------------------------------------------

	private static String encodeValue(Object v) {
		if (v == null)              return "N:";
		if (v instanceof Integer)   return "I:" + v;
		if (v instanceof Boolean)   return "B:" + v;
		return "S:" + v;
	}

	private static Object decodeValue(String encoded) {
		if (encoded.startsWith("N:")) return null;
		if (encoded.startsWith("I:")) return Integer.parseInt(encoded.substring(2));
		if (encoded.startsWith("B:")) return Boolean.parseBoolean(encoded.substring(2));
		if (encoded.startsWith("S:")) return encoded.substring(2);
		return encoded; // fallback: treat as raw string
	}

	// -------------------------------------------------------------------------
	// Table mutations (delegate to HashTable, then flush to disk)
	// -------------------------------------------------------------------------

	@Override
	public void clear() {
		inMemory.clear();
		flush();
	}

	@Override
	public List<Object> put(String key, List<Object> values) {
		List<Object> old = inMemory.put(key, values); // throws IllegalArgumentException on bad values size
		flush();
		return old;
	}

	@Override
	public List<Object> remove(String key) {
		List<Object> old = inMemory.remove(key);
		if (old != null) flush();
		return old;
	}

	// -------------------------------------------------------------------------
	// Read-only delegation
	// -------------------------------------------------------------------------

	@Override
	public List<Object> get(String key) {
		return inMemory.get(key);
	}

	@Override
	public int degree() {
		return inMemory.degree();
	}

	@Override
	public int size() {
		return inMemory.size();
	}

	@Override
	public int hashCode() {
		return inMemory.hashCode();
	}

	@Override
	public boolean equals(Object obj) {
		return obj instanceof Table && this.hashCode() == obj.hashCode();
	}

	@Override
	public Iterator<Row> iterator() {
		return inMemory.iterator();
	}

	@Override
	public String name() {
		return inMemory.name();
	}

	@Override
	public List<String> columns() {
		return inMemory.columns();
	}

	@Override
	public String toString() {
		return toPrettyString();
	}

	// -------------------------------------------------------------------------
	// Internal helpers
	// -------------------------------------------------------------------------

	private void writeHeader() throws IOException {
		try (PrintWriter pw = new PrintWriter(Files.newBufferedWriter(csvFile))) {
			pw.println(String.join(",", inMemory.columns()));
		}
	}
}
