package features;

public interface DataTable extends Table {
	public int capacity();

	public default boolean isFull() {
		return size() == capacity();
	}

	public default double loadFactor() {
		return (double) size() / capacity();
	}
}
