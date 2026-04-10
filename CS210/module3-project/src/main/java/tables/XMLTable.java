package tables;

import java.io.FileWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Iterator;
import java.util.List;

import org.dom4j.Document;
import org.dom4j.DocumentException;
import org.dom4j.DocumentFactory;
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

			// TODO populate metadata in the tree

			flush();

//			throw new UnsupportedOperationException("Implement rest of 2-parameter constructor for Module 4");
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
		throw new UnsupportedOperationException("Implement clear for Module 4");
	}

	@Override
	public List<Object> put(String key, List<Object> values) {
		throw new UnsupportedOperationException("Implement put for Module 4");
	}

	@Override
	public List<Object> get(String key) {
		throw new UnsupportedOperationException("Implement get for Module 4");
	}

	@Override
	public List<Object> remove(String key) {
		throw new UnsupportedOperationException("Implement remove for Module 4");
	}

	@Override
	public int degree() {
		throw new UnsupportedOperationException("Implement degree for Module 4");
	}

	@Override
	public int size() {
		throw new UnsupportedOperationException("Implement size for Module 4");
	}

	@Override
	public int hashCode() {
		throw new UnsupportedOperationException("Implement hashCode (fingerprint) for Module 4");
	}

	@Override
	public boolean equals(Object obj) {
		return obj instanceof Table &&
			this.hashCode() == obj.hashCode();
	}

	@Override
	public Iterator<Row> iterator() {
		throw new UnsupportedOperationException("Implement iterator for Module 4");

	}

	@Override
	public String name() {
		throw new UnsupportedOperationException("Implement name for Module 4");
	}

	@Override
	public List<String> columns() {
		throw new UnsupportedOperationException("Implement columns for Module 4");
	}

	@Override
	public String toString() {
		return toPrettyString();
	}
}