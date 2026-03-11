package tables;

import java.util.Iterator;
import java.util.List;

import features.DataTable;
import features.PrettyTable;
import features.Table;

public class SymbolTable implements DataTable, PrettyTable {
	private static final int CAPACITY = 52;

	private final String tableName;
	private final List<String> columnNames;
	private Row[] rows;
	private int size;
	private int fingerprint;

	public SymbolTable(String name, List<String> columns) {
		this.tableName = name;
		this.columnNames = columns;
		clear();
	}

	@Override
	public void clear() {
		rows = new Row[CAPACITY];
		size = 0;
		fingerprint = 0;
	}

	private int addressOf(String key) {
		if (key == null || key.isEmpty()) {
			return -1;
		}
		char first = key.charAt(0);
		if (first >= 'a' && first <= 'z') {
			return first - 'a';
		} else if (first >= 'A' && first <= 'Z') {
			return 26 + (first - 'A');
		}
		return -1;
	}

	@Override
	public List<Object> put(String key, List<Object> values) {
		if (key == null || key.isEmpty()) {
			throw new IllegalArgumentException("Key cannot be null or empty");
		}
		if (values == null || values.size() != degree() - 1) {
			throw new IllegalArgumentException("Values must have exactly " + (degree() - 1) + " elements");
		}

		int address = addressOf(key);
		if (address < 0 || address >= CAPACITY) {
			throw new IllegalArgumentException("Invalid key: first character must be a letter");
		}

		Row oldRow = rows[address];
		Row newRow = new Row(key, values);
		rows[address] = newRow;

		if (oldRow != null) {
			fingerprint -= oldRow.hashCode();
			fingerprint += newRow.hashCode();
			return oldRow.values();
		} else {
			size++;
			fingerprint += newRow.hashCode();
			return null;
		}
	}

	@Override
	public List<Object> get(String key) {
		if (key == null || key.isEmpty()) {
			throw new IllegalArgumentException("Key cannot be null or empty");
		}

		int address = addressOf(key);
		if (address < 0 || address >= CAPACITY) {
			return null;
		}

		Row row = rows[address];
		if (row != null) {
			return row.values();
		}
		return null;
	}

	@Override
	public List<Object> remove(String key) {
		if (key == null || key.isEmpty()) {
			throw new IllegalArgumentException("Key cannot be null or empty");
		}

		int address = addressOf(key);
		if (address < 0 || address >= CAPACITY) {
			return null;
		}

		Row oldRow = rows[address];
		if (oldRow != null) {
			rows[address] = null;
			size--;
			fingerprint -= oldRow.hashCode();
			return oldRow.values();
		}
		return null;
	}

	@Override
	public int degree() {
		return columnNames.size();
	}

	@Override
	public int size() {
		return size;
	}

	@Override
	public int capacity() {
		return CAPACITY;
	}

	@Override
	public int hashCode() {
		return fingerprint;
	}

	@Override
	public boolean equals(Object obj) {
		if (obj instanceof Table other) {
			return this.hashCode() == other.hashCode();
		}
		return false;
	}

	@Override
	public Iterator<Row> iterator() {
		return new Iterator<>() {
			private int current = 0;

			@Override
			public boolean hasNext() {
				while (current < CAPACITY && rows[current] == null) {
					current++;
				}
				return current < CAPACITY;
			}

			@Override
			public Row next() {
				while (current < CAPACITY && rows[current] == null) {
					current++;
				}
				if (current < CAPACITY) {
					return rows[current++];
				}
				return null;
			}
		};
	}

	@Override
	public String name() {
		return tableName;
	}

	@Override
	public List<String> columns() {
		return columnNames;
	}

	@Override
	public String toString() {
		return toPrettyString();
	}
}
