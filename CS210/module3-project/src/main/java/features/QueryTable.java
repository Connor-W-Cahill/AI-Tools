package features;

import java.util.List;

public interface QueryTable extends Table {
	public default QueryTable select(String column, Object criteria) {
		throw new UnsupportedOperationException("Implement API's select for Module 3");
	}

	public default QueryTable project(List<String> columns) {
		throw new UnsupportedOperationException("Implement API's project for Module 3");
	}

	public default QueryTable union(QueryTable table) {
		throw new UnsupportedOperationException("Implement API's union for Module 4");
	}

	public default QueryTable intersect(QueryTable table) {
		throw new UnsupportedOperationException("Implement API's intersect for Module 4");
	}

	public default QueryTable minus(QueryTable table) {
		throw new UnsupportedOperationException("Implement API's minus for Module 4");
	}
}
