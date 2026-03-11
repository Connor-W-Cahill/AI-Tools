package apps;

import java.util.List;

import features.FileTable;
import features.Table;
import tables.CSVTable;

public class Sandbox {
	public static void main(String[] args) {

		// CSVTable 1: Video Games — new table, put/get/remove, then reopen from disk
		FileTable VG = new CSVTable("csv_video_games", List.of("title", "genre", "year", "multiplayer"));
		VG.put("Minecraft",   List.of("sandbox",    2011, true));
		VG.put("Zelda: BOTW", List.of("adventure",  2017, false));
		VG.put("Elden Ring",  List.of("action RPG", 2022, true));
		VG.put("Portal 2",    List.of("puzzle",      2011, true));
		VG.put("Hades",       List.of("roguelike",   2020, false));
		System.out.println("After 5 inserts (new table):");
		System.out.println(VG);

		System.out.println("Get 'Minecraft': "      + VG.get("Minecraft"));
		System.out.println("Get 'Missing' (miss): " + VG.get("Missing"));

		List<Object> oldHades = VG.put("Hades", List.of("roguelike", 2018, false));
		System.out.println("Updated 'Hades', old year was: " + oldHades.get(1));

		VG.remove("Portal 2");
		System.out.println("Removed 'Portal 2', size now: " + VG.size());

		// Demonstrate persistence: reopen the same file
		System.out.println("\n--- Reopening csv_video_games from disk ---");
		FileTable VG2 = new CSVTable("csv_video_games");
		System.out.println("name:    "  + VG2.name());
		System.out.println("columns: "  + VG2.columns());
		System.out.println("size:    "  + VG2.size());
		System.out.println("fingerprints match: " + (VG.hashCode() == VG2.hashCode()));
		System.out.println(VG2);

		// CSVTable 2: Programming Languages — iterator and clear
		FileTable PL = new CSVTable("csv_prog_langs", List.of("lang", "paradigm", "typed"));
		PL.put("Java",       List.of("OOP",            "static"));
		PL.put("Python",     List.of("multi-paradigm", "dynamic"));
		PL.put("Rust",       List.of("systems",        "static"));
		PL.put("JavaScript", List.of("multi-paradigm", "dynamic"));

		System.out.println("\n--- Iterator demo ---");
		for (Table.Row row : PL) {
			System.out.println("  " + row.key() + " -> " + row.values());
		}

		System.out.println("\nBefore clear: size=" + PL.size());
		PL.clear();
		System.out.println("After  clear: size=" + PL.size() + ", isEmpty=" + PL.isEmpty());

		FileTable PL2 = new CSVTable("csv_prog_langs");
		System.out.println("Reopened after clear: size=" + PL2.size() + " (expected 0)");

		// CSVTable 3: Type preservation across flush/reopen
		FileTable TV = new CSVTable("csv_types", List.of("key", "str_val", "int_val", "bool_val", "null_val"));
		TV.put("row1", List.of("hello",  42, true,  null));
		TV.put("row2", List.of("world", -7, false, null));
		System.out.println("\n--- Type preservation ---");
		System.out.println(TV);

		FileTable TV2 = new CSVTable("csv_types");
		List<Object> r1 = TV2.get("row1");
		System.out.println("str_val  is String:  " + (r1.get(0) instanceof String)  + " → " + r1.get(0));
		System.out.println("int_val  is Integer: " + (r1.get(1) instanceof Integer)  + " → " + r1.get(1));
		System.out.println("bool_val is Boolean: " + (r1.get(2) instanceof Boolean)  + " → " + r1.get(2));
		System.out.println("null_val is null:    " + (r1.get(3) == null));
		System.out.println("fingerprints match:  " + (TV.hashCode() == TV2.hashCode()));
	}
}
