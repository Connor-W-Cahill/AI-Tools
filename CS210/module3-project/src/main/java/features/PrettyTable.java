package features;

import java.util.Objects;
import java.util.StringJoiner;

public interface PrettyTable extends Table {
	public default String toPrettyString() {
		var widths = new int[degree()];

		for (var i = 0; i < columns().size(); i++)
			widths[i] = Math.max(10, columns().get(i).length());

		widths[0] = Math.max(widths[0], name().length());

		for (var row: this) {
			widths[0] = Math.max(widths[0], row.key().length());
			for (var i = 0; i < row.values().size(); i++)
				widths[i+1] = Math.max(widths[i + 1], String.valueOf(row.values().get(i)).length());
		}

		var crown = ("| %-" + widths[0] + "s |\n").formatted(name());

		var head = new StringJoiner(" | ", "| ", " |\n");
		for (var i = 0; i < columns().size(); i++)
			head.add(("%-" + widths[i] + "s").formatted(columns().get(i)));

		var body = new StringBuilder();
		for (var row: this) {
			var current = new StringJoiner(" | ", "| ", " |\n");
			current.add(("%-" + widths[0] + "s").formatted(row.key()));
			for (var i = 0; i < row.values().size(); i++)
				current.add(("%-" + widths[i + 1] + "s").formatted(Objects.requireNonNullElse(row.values().get(i), ""), widths[i + 1]));
			body.append(current);
		}

		var thin = "+" + "-".repeat(crown.length() - 3) + "+ \n";
		var wide = "+" + "-".repeat(head.length() - 3) + "+\n";

		return thin + crown + wide + head + wide + body + wide;
	}
}
