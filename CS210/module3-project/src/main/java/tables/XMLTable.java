package tables;

import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Iterator;
import java.util.List;

import org.dom4j.Document;
import org.dom4j.DocumentException;
import org.dom4j.DocumentFactory;
import org.dom4j.Element;
import org.dom4j.io.SAXReader;
import org.dom4j.io.XMLWriter;

import features.FileTable;
import features.PrettyTable;
import features.QueryTable;
import features.Table;

public class XMLTable implements FileTable, QueryTable, PrettyTable {
	private static final Path baseDir = Paths.get("db", "tables");
	private final Path xmlFile;

	private static final DocumentFactory helper = DocumentFactory.getInstance();
	private final Document doc;

	public XMLTable(String newName, List<String> newColumns) {
		try {
			Files.createDirectories(baseDir);

			xmlFile = baseDir.resolve(newName + ".xml");
			if (Files.notExists(xmlFile))
				Files.createFile(xmlFile);

			doc = helper.createDocument();

			var root = doc.addElement("table");
			root.addAttribute("name", newName);
			var colsElem = root.addElement("columns");
			for (String col : newColumns) {
				colsElem.addElement("column").addText(col);
			}
			root.addElement("rows");

			flush();
		}
		catch (IOException e) {
			throw new IllegalStateException(e);
		}
	}

	public XMLTable(String existingName) {
		try {
			xmlFile = baseDir.resolve(existingName + ".xml");

			if (Files.notExists(xmlFile))
				throw new IllegalArgumentException("Missing table: " + existingName);

			doc = new SAXReader().read(xmlFile.toFile());
		}
		catch (DocumentException e) {
			throw new IllegalStateException(e);
		}
	}

	@Override
	public void flush() {
		try {
			var writer = new XMLWriter(new FileWriter(xmlFile.toFile()));
	        writer.write(doc);
	        writer.close();
		}
		catch (IOException e) {
			throw new IllegalStateException(e);
		}
	}

	@Override
	public void clear() {
		doc.getRootElement().element("rows").clearContent();
		flush();
	}

	@Override
	public List<Object> put(String key, List<Object> values) {
		var cols = columns();
		if (values == null || values.size() != cols.size() - 1)
			throw new IllegalArgumentException("Wrong number of values: expected " + (cols.size() - 1));

		var rowsElem = doc.getRootElement().element("rows");

		for (var rowElem : rowsElem.elements("row")) {
			if (rowElem.attributeValue("key").equals(key)) {
				var old = decodeRowValues(rowElem);
				rowElem.clearContent();
				encodeValues(rowElem, values);
				flush();
				return old;
			}
		}

		var rowElem = rowsElem.addElement("row");
		rowElem.addAttribute("key", key);
		encodeValues(rowElem, values);
		flush();
		return null;
	}

	@Override
	public List<Object> get(String key) {
		var rowsElem = doc.getRootElement().element("rows");
		for (var rowElem : rowsElem.elements("row")) {
			if (rowElem.attributeValue("key").equals(key)) {
				return decodeRowValues(rowElem);
			}
		}
		return null;
	}

	@Override
	public List<Object> remove(String key) {
		var rowsElem = doc.getRootElement().element("rows");
		for (var rowElem : rowsElem.elements("row")) {
			if (rowElem.attributeValue("key").equals(key)) {
				var old = decodeRowValues(rowElem);
				rowElem.detach();
				flush();
				return old;
			}
		}
		return null;
	}

	@Override
	public int degree() {
		return columns().size();
	}

	@Override
	public int size() {
		return doc.getRootElement().element("rows").elements("row").size();
	}

	@Override
	public int hashCode() {
		int fingerprint = 0;
		for (var rowElem : doc.getRootElement().element("rows").elements("row")) {
			var key = rowElem.attributeValue("key");
			var values = decodeRowValues(rowElem);
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
		var list = new ArrayList<Row>();
		for (var rowElem : doc.getRootElement().element("rows").elements("row")) {
			var key = rowElem.attributeValue("key");
			var values = decodeRowValues(rowElem);
			list.add(new Row(key, Collections.unmodifiableList(values)));
		}
		return list.iterator();
	}

	@Override
	public String name() {
		return doc.getRootElement().attributeValue("name");
	}

	@Override
	public List<String> columns() {
		var colsElem = doc.getRootElement().element("columns");
		var result = new ArrayList<String>();
		for (var col : colsElem.elements("column")) {
			result.add(col.getText());
		}
		return Collections.unmodifiableList(result);
	}

	@Override
	public String toString() {
		return toPrettyString();
	}

	private static void encodeValues(Element rowElem, List<Object> values) {
		for (Object v : values) {
			var valElem = rowElem.addElement("value");
			if (v == null) {
				valElem.addAttribute("type", "null");
			} else if (v instanceof String s) {
				valElem.addAttribute("type", "string");
				valElem.addText(s);
			} else if (v instanceof Integer i) {
				valElem.addAttribute("type", "int");
				valElem.addText(i.toString());
			} else if (v instanceof Boolean b) {
				valElem.addAttribute("type", "bool");
				valElem.addText(b.toString());
			}
		}
	}

	private static List<Object> decodeRowValues(Element rowElem) {
		var result = new ArrayList<Object>();
		for (var valElem : rowElem.elements("value")) {
			switch (valElem.attributeValue("type")) {
				case "null"   -> result.add(null);
				case "string" -> result.add(valElem.getText());
				case "int"    -> result.add(Integer.parseInt(valElem.getText()));
				case "bool"   -> result.add(Boolean.parseBoolean(valElem.getText()));
			}
		}
		return Collections.unmodifiableList(result);
	}
}
