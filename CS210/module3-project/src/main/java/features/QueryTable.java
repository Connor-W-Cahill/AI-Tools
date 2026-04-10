package features;

import java.util.List;

import tables.HashTable;

public interface QueryTable extends Table {

	public default QueryTable select(String column, Object criteria) {
		List<String> cols = columns();
		int idx = cols.indexOf(column);
		HashTable result = new HashTable(name() + "_select", cols);
		for (Row row : this) {
			Object val = (idx == 0) ? row.key() : row.values().get(idx - 1);
			if (criteria == null ? val == null : criteria.equals(val)) {
				result.put(row.key(), row.values());
			}
		}
		return result;
	}

	public default QueryTable project(List<String> columns) {
		throw new UnsupportedOperationException("Implement API's project for Module 3");
	}

	public default QueryTable union(QueryTable table) {
		HashTable result = new HashTable(name() + "_union", columns());
		for (Row row : this)
			result.put(row.key(), row.values());
		for (Row row : table)
			if (!result.contains(row.key()))
				result.put(row.key(), row.values());
		return result;
	}

	public default QueryTable intersect(QueryTable table) {
		HashTable result = new HashTable(name() + "_intersect", columns());
		for (Row row : this)
			if (table.contains(row.key()))
				result.put(row.key(), row.values());
		return result;
	}

	public default QueryTable minus(QueryTable table) {
		HashTable result = new HashTable(name() + "_minus", columns());
		for (Row row : this)
			if (!table.contains(row.key()))
				result.put(row.key(), row.values());
		return result;
	}
}
