package tables;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;

import features.FileTable;
import features.PrettyTable;
import features.QueryTable;
import features.Table;
import tools.jackson.core.exc.StreamReadException;
import tools.jackson.core.exc.StreamWriteException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.ObjectMapper;
import tools.jackson.databind.node.ArrayNode;
import tools.jackson.databind.node.ObjectNode;

public class JSONTable implements FileTable, QueryTable, PrettyTable {
	private static final Path baseDir = Paths.get("db", "tables");
	private final Path jsonFile;

	private static final ObjectMapper helper = new ObjectMapper();
	private final ObjectNode tree;

	public JSONTable(String newName, List<String> newColumns) {
		try {
			Files.createDirectories(baseDir);

			jsonFile = baseDir.resolve(newName + ".json");
			if (Files.notExists(jsonFile))
				Files.createFile(jsonFile);

			tree = helper.createObjectNode();

			tree.put("name", newName);
			var columnsArray = helper.createArrayNode();
			for (String col : newColumns) {
				columnsArray.add(col);
			}
			tree.set("columns", columnsArray);
			tree.set("rows", helper.createObjectNode());

			flush();
		}
		catch (IOException e) {
			throw new IllegalStateException(e);
		}
	}

	public JSONTable(String existingName) {
		try {
			jsonFile = baseDir.resolve(existingName + ".json");

			if (Files.notExists(jsonFile))
				throw new IllegalArgumentException("Missing table: " + existingName);

			tree = (ObjectNode) helper.readTree(jsonFile.toFile());
		}
		catch (StreamReadException e) {
			throw new IllegalStateException(e);
		}
	}

	@Override
	public void flush() {
		try {
			helper.writerWithDefaultPrettyPrinter().writeValue(jsonFile.toFile(), tree);
		}
		catch (StreamWriteException e) {
			throw new IllegalStateException(e);
		}
	}

	@Override
	public void clear() {
		((ObjectNode) tree.get("rows")).removeAll();
		flush();
	}

	@Override
	public List<Object> put(String key, List<Object> values) {
		if (key == null || key.isEmpty())
			throw new IllegalArgumentException("Key cannot be null or empty");
		var cols = columns();
		if (values == null || values.size() != cols.size() - 1)
			throw new IllegalArgumentException("Wrong number of values: expected " + (cols.size() - 1));

		var rows = (ObjectNode) tree.get("rows");
		var existingNode = rows.get(key);
		List<Object> old = null;

		if (existingNode != null) {
			old = decodeValues(existingNode);
		}

		var arr = helper.createArrayNode();
		for (Object v : values) {
			encodeValue(arr, v);
		}
		rows.set(key, arr);
		flush();
		return old;
	}

	@Override
	public List<Object> get(String key) {
		if (key == null || key.isEmpty()) return null;
		var rows = (ObjectNode) tree.get("rows");
		var node = rows.get(key);
		if (node == null) return null;
		return decodeValues(node);
	}

	@Override
	public List<Object> remove(String key) {
		if (key == null || key.isEmpty()) return null;
		var rows = (ObjectNode) tree.get("rows");
		var node = rows.get(key);
		if (node == null) return null;
		var old = decodeValues(node);
		rows.remove(key);
		flush();
		return old;
	}

	@Override
	public int degree() {
		return columns().size();
	}

	@Override
	public int size() {
		return tree.get("rows").size();
	}

	@Override
	public int hashCode() {
		int fingerprint = 0;
		var rows = (ObjectNode) tree.get("rows");
		for (var entry : rows.properties()) {
			var key = entry.getKey();
			var values = decodeValues(entry.getValue());
			fingerprint += new Row(key, values).hashCode();
		}
		return fingerprint;
	}

	@Override
	public boolean equals(Object obj) {
		return obj instanceof Table &&
			this.hashCode() == obj.hashCode();
	}

	@Override
	public Iterator<Row> iterator() {
		var rows = (ObjectNode) tree.get("rows");
		var list = new ArrayList<Row>();
		for (var entry : rows.properties()) {
			var key = entry.getKey();
			var values = decodeValues(entry.getValue());
			list.add(new Row(key, Collections.unmodifiableList(values)));
		}
		return list.iterator();
	}

	@Override
	public String name() {
		return tree.get("name").textValue();
	}

	@Override
	public List<String> columns() {
		var colArray = tree.get("columns");
		var result = new ArrayList<String>();
		for (var node : colArray) {
			result.add(node.textValue());
		}
		return Collections.unmodifiableList(result);
	}

	@Override
	public String toString() {
		return toPrettyString();
	}

	private static void encodeValue(ArrayNode arr, Object v) {
		if (v == null)
			arr.addNull();
		else if (v instanceof String s)
			arr.add(s);
		else if (v instanceof Integer i)
			arr.add(i);
		else if (v instanceof Boolean b)
			arr.add(b);
	}

	private static List<Object> decodeValues(JsonNode arr) {
		var result = new ArrayList<Object>();
		for (var node : arr) {
			if (node.isNull())
				result.add(null);
			else if (node.isTextual())
				result.add(node.textValue());
			else if (node.isInt())
				result.add(node.intValue());
			else if (node.isBoolean())
				result.add(node.booleanValue());
			else
				result.add(null);
		}
		return Collections.unmodifiableList(result);
	}
}
