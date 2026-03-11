package features;

import java.util.Iterator;
import java.util.List;

import features.Table.Row;

public interface Table extends Iterable<Row> {
	public record Row(String key, List<Object> values) {}

	public void clear();

	public List<Object> put(String key, List<Object> values);

	public List<Object> get(String key);

	public List<Object> remove(String key);

	public default boolean contains(String key) {
		return get(key) != null;
	}

	public int degree();

	public int size();

	public default boolean isEmpty() {
		return size() == 0;
	}

	@Override
	public int hashCode();

	@Override
	public boolean equals(Object obj);

	@Override
	public Iterator<Row> iterator();

	public String name();

	public List<String> columns();

	@Override
	public String toString();
}
