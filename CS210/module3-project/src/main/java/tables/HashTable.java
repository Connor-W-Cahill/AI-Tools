package tables;

import java.util.Iterator;
import java.util.List;
import java.util.NoSuchElementException;

import features.DataTable;
import features.PrettyTable;
import features.QueryTable;
import features.Table;

public class HashTable implements DataTable, QueryTable, PrettyTable {
	private static final int INITIAL_CAPACITY = 8;
	private static final double LOAD_FACTOR_THRESHOLD = 0.75;
	private static final Row SENTINEL = new Row(null, null);
	private static final String SALT = "ConnorCahill";

	private final String tableName;
	private final List<String> columnNames;
	private Row[] rows;
	private int size;
	private int fingerprint;
	private int capacity;

	public HashTable(String name, List<String> columns) {
		this.tableName = name;
		this.columnNames = columns;
		clear();
	}

	@Override
	public void clear() {
		capacity = INITIAL_CAPACITY;
		rows = new Row[capacity];
		size = 0;
		fingerprint = 0;
	}

	private int hashFunction(String key) {
		String salted = key + SALT;
		int hash = 0;
		for (int i = 0; i < salted.length(); i++) {
			hash = hash * 31 + salted.charAt(i);
		}
		return Math.floorMod(hash, capacity);
	}

	private int doubleHash(String key) {
		String salted = key + SALT;
		int hash = 0x811c9dc5; // FNV offset basis (2166136261 as signed int)
		for (int i = 0; i < salted.length(); i++) {
			hash ^= salted.charAt(i);
			hash *= 0x01000193; // FNV prime (16777619)
		}
		return Math.floorMod(hash, capacity) | 1; // ensure odd for coprimality with power-of-2
	}

	@Override
	public List<Object> put(String key, List<Object> values) {
		if (key == null || key.isEmpty()) {
			throw new IllegalArgumentException("Key cannot be null or empty");
		}
		if (values == null || values.size() != degree() - 1) {
			throw new IllegalArgumentException("Values must have exactly " + (degree() - 1) + " elements");
		}

		int h1 = hashFunction(key);
		int h2 = doubleHash(key);
		int firstSentinel = -1;

		for (int i = 0; i < capacity; i++) {
			int index = Math.floorMod(h1 + i * h2, capacity);
			Row slot = rows[index];

			if (slot == null) {
				int insertAt = (firstSentinel >= 0) ? firstSentinel : index;
				Row newRow = new Row(key, values);
				rows[insertAt] = newRow;
				size++;
				fingerprint += newRow.hashCode();
				if (loadFactor() >= LOAD_FACTOR_THRESHOLD) {
					rehash();
				}
				return null;
			}

			if (slot == SENTINEL) {
				if (firstSentinel < 0) {
					firstSentinel = index;
				}
				continue;
			}

			if (slot.key().equals(key)) {
				Row newRow = new Row(key, values);
				rows[index] = newRow;
				fingerprint -= slot.hashCode();
				fingerprint += newRow.hashCode();
				return slot.values();
			}
		}

		if (firstSentinel >= 0) {
			Row newRow = new Row(key, values);
			rows[firstSentinel] = newRow;
			size++;
			fingerprint += newRow.hashCode();
			if (loadFactor() >= LOAD_FACTOR_THRESHOLD) {
				rehash();
			}
			return null;
		}

		rehash();
		return put(key, values);
	}

	@Override
	public List<Object> get(String key) {
		if (key == null || key.isEmpty()) {
			return null;
		}

		int h1 = hashFunction(key);
		int h2 = doubleHash(key);

		for (int i = 0; i < capacity; i++) {
			int index = Math.floorMod(h1 + i * h2, capacity);
			Row slot = rows[index];

			if (slot == null) {
				return null;
			}

			if (slot != SENTINEL && slot.key().equals(key)) {
				return slot.values();
			}
		}

		return null;
	}

	@Override
	public List<Object> remove(String key) {
		if (key == null || key.isEmpty()) {
			return null;
		}

		int h1 = hashFunction(key);
		int h2 = doubleHash(key);

		for (int i = 0; i < capacity; i++) {
			int index = Math.floorMod(h1 + i * h2, capacity);
			Row slot = rows[index];

			if (slot == null) {
				return null;
			}

			if (slot != SENTINEL && slot.key().equals(key)) {
				rows[index] = SENTINEL;
				size--;
				fingerprint -= slot.hashCode();
				return slot.values();
			}
		}

		return null;
	}

	private void rehash() {
		Row[] oldRows = rows;
		capacity *= 2;
		rows = new Row[capacity];
		size = 0;
		fingerprint = 0;

		for (Row row : oldRows) {
			if (row != null && row != SENTINEL) {
				put(row.key(), row.values());
			}
		}
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
		return capacity;
	}

	@Override
	public int hashCode() {
		return fingerprint;
	}

	@Override
	public boolean equals(Object obj) {
		return obj instanceof Table &&
			this.hashCode() == obj.hashCode();
	}

	@Override
	public Iterator<Row> iterator() {
		return new Iterator<>() {
			private int current = 0;

			@Override
			public boolean hasNext() {
				while (current < capacity && (rows[current] == null || rows[current] == SENTINEL)) {
					current++;
				}
				return current < capacity;
			}

			@Override
			public Row next() {
				while (current < capacity && (rows[current] == null || rows[current] == SENTINEL)) {
					current++;
				}
				if (current < capacity) {
					return rows[current++];
				}
				throw new NoSuchElementException();
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
