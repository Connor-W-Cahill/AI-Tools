package features;

import java.io.Flushable;

public interface FileTable extends Table, Flushable, AutoCloseable {
	@Override
	public default void flush() {}

	@Override
	public default void close() {
		flush();
	}
}
