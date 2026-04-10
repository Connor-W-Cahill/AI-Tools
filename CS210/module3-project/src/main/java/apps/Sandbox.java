package apps;

import java.util.Arrays;
import java.util.List;

import features.FileTable;
import features.QueryTable;
import features.Table;
import tables.CSVTable;
import tables.JSONTable;

public class Sandbox {
	public static void main(String[] args) {

		// -------------------------------------------------------------------------
		// CSVTable 1: Video Games
		// Demonstrates: create, put (miss + hit), get, remove, degree, size,
		//               hashCode, iterator, reopen constructor
		// -------------------------------------------------------------------------
		CSVTable games = new CSVTable("csv_games", List.of("title", "genre", "year", "solo"));
		games.put("Minecraft",    List.of("sandbox",    2011, true));
		games.put("Elden Ring",   List.of("action RPG", 2022, true));
		games.put("Stardew",      List.of("simulation", 2016, true));
		games.put("Terraria",     List.of("sandbox",    2011, true));
		games.put("Hades",        List.of("roguelike",  2020, true));
		games.put("Among Us",     List.of("social",     2018, false));
		games.put("Valheim",      List.of("survival",   2021, false));
		System.out.println("=== csv_games (new) ===");
		System.out.println(games);
		System.out.println("degree=" + games.degree() + "  size=" + games.size());

		// hit — returns old values
		List<Object> old = games.put("Hades", List.of("roguelike", 2018, true));
		System.out.println("Updated Hades: old year=" + old.get(1) + "  new year=" + games.get("Hades").get(1));

		// miss — returns null
		System.out.println("Get missing key: " + games.get("Pong"));

		// remove hit and miss
		System.out.println("Removed Among Us: " + games.remove("Among Us"));
		System.out.println("Remove missing:   " + games.remove("Pong"));
		System.out.println("Size after removes: " + games.size());

		// iterator
		System.out.println("\nIterating csv_games:");
		for (Table.Row row : games) {
			System.out.println("  " + row.key() + " -> " + row.values());
		}

		// reopen — verify fingerprint survives disk round-trip
		CSVTable games2 = new CSVTable("csv_games");
		System.out.println("\n=== csv_games (reopened) ===");
		System.out.println("name=" + games2.name() + "  columns=" + games2.columns());
		System.out.println("size=" + games2.size() + "  fingerprints match: " + (games.hashCode() == games2.hashCode()));
		System.out.println(games2);

		// -------------------------------------------------------------------------
		// CSVTable 2: Albums
		// Demonstrates: create, clear, reopen, select on string column,
		//               select on integer column, select on boolean column
		// -------------------------------------------------------------------------
		CSVTable albums = new CSVTable("csv_albums", List.of("album", "artist", "year", "explicit"));
		albums.put("OK Computer",        List.of("Radiohead",    1997, false));
		albums.put("The Dark Side",      List.of("Pink Floyd",   1973, false));
		albums.put("To Pimp a Butterfly", List.of("Kendrick",    2015, true));
		albums.put("DAMN.",              List.of("Kendrick",     2017, true));
		albums.put("Abbey Road",         List.of("Beatles",      1969, false));
		albums.put("Thriller",           List.of("MJ",           1982, false));
		albums.put("Nevermind",          List.of("Nirvana",      1991, false));
		System.out.println("\n=== csv_albums (new) ===");
		System.out.println(albums);

		// select: albums by Kendrick
		QueryTable byKendrick = albums.select("artist", "Kendrick");
		System.out.println("select artist=Kendrick  (size=" + byKendrick.size() + "):");
		System.out.println(byKendrick);

		// select: albums from 1973
		QueryTable from1973 = albums.select("year", 1973);
		System.out.println("select year=1973  (size=" + from1973.size() + "):");
		System.out.println(from1973);

		// select: explicit albums
		QueryTable explicit = albums.select("explicit", true);
		System.out.println("select explicit=true  (size=" + explicit.size() + "):");
		System.out.println(explicit);

		// select: no matches
		QueryTable none = albums.select("artist", "Drake");
		System.out.println("select artist=Drake  (size=" + none.size() + ", expected 0)");

		// clear and reopen to verify cleared state persists
		albums.clear();
		System.out.println("After clear: size=" + albums.size());
		CSVTable albums2 = new CSVTable("csv_albums");
		System.out.println("Reopened after clear: size=" + albums2.size() + " (expected 0)");

		// -------------------------------------------------------------------------
		// CSVTable 3: Planets
		// Demonstrates: null values, type preservation, fingerprint after reopen
		// -------------------------------------------------------------------------
		CSVTable planets = new CSVTable("csv_planets",
			List.of("planet", "type", "moons", "rings", "life"));
		planets.put("Mercury", Arrays.asList("terrestrial",  0,  false, null));
		planets.put("Venus",   Arrays.asList("terrestrial",  0,  false, null));
		planets.put("Earth",   List.of("terrestrial",  1,  false, true));
		planets.put("Mars",    List.of("terrestrial",  2,  false, false));
		planets.put("Jupiter", List.of("gas giant",    95, true,  false));
		planets.put("Saturn",  List.of("gas giant",    146, true, false));
		planets.put("Uranus",  List.of("ice giant",    28, true,  false));
		planets.put("Neptune", List.of("ice giant",    16, true,  false));
		System.out.println("\n=== csv_planets (new) ===");
		System.out.println(planets);

		// select gas giants
		QueryTable gasGiants = planets.select("type", "gas giant");
		System.out.println("select type='gas giant'  (size=" + gasGiants.size() + "):");
		System.out.println(gasGiants);

		// select null life (unknown)
		QueryTable unknownLife = planets.select("life", null);
		System.out.println("select life=null  (size=" + unknownLife.size() + "):");
		System.out.println(unknownLife);

		// reopen and verify types survive disk round-trip
		CSVTable planets2 = new CSVTable("csv_planets");
		List<Object> earth = planets2.get("Earth");
		System.out.println("\nEarth after reopen:");
		System.out.println("  type  is String:  " + (earth.get(0) instanceof String)  + " = " + earth.get(0));
		System.out.println("  moons is Integer: " + (earth.get(1) instanceof Integer)  + " = " + earth.get(1));
		System.out.println("  rings is Boolean: " + (earth.get(2) instanceof Boolean)  + " = " + earth.get(2));
		System.out.println("  life  is Boolean: " + (earth.get(3) instanceof Boolean)  + " = " + earth.get(3));
		System.out.println("fingerprints match: " + (planets.hashCode() == planets2.hashCode()));

		// -------------------------------------------------------------------------
		// JSONTable 1: Albums
		// Demonstrates: create, put (miss + hit), get, remove, degree, size,
		//               hashCode, iterator, reopen constructor
		// -------------------------------------------------------------------------
		JSONTable albums_json = new JSONTable("json_albums", List.of("album", "artist", "year", "explicit"));
		albums_json.put("OK Computer",         List.of("Radiohead",   1997, false));
		albums_json.put("To Pimp a Butterfly", List.of("Kendrick",    2015, true));
		albums_json.put("DAMN.",               List.of("Kendrick",    2017, true));
		albums_json.put("Abbey Road",          List.of("Beatles",     1969, false));
		albums_json.put("Thriller",            List.of("MJ",          1982, false));
		albums_json.put("Nevermind",           List.of("Nirvana",     1991, false));
		albums_json.put("Blonde",              List.of("Frank Ocean", 2016, false));
		System.out.println("\n=== json_albums (new) ===");
		System.out.println(albums_json);
		System.out.println("degree=" + albums_json.degree() + "  size=" + albums_json.size());

		// hit — returns old values
		List<Object> oldAlbum = albums_json.put("DAMN.", List.of("Kendrick Lamar", 2017, true));
		System.out.println("Updated DAMN.: old artist=" + oldAlbum.get(0) + "  new artist=" + albums_json.get("DAMN.").get(0));

		// miss — returns null
		System.out.println("Get missing key: " + albums_json.get("Graduation"));

		// remove hit and miss
		System.out.println("Removed Thriller: " + albums_json.remove("Thriller"));
		System.out.println("Remove missing:   " + albums_json.remove("Graduation"));
		System.out.println("Size after remove: " + albums_json.size());

		// iterator
		System.out.println("\nIterating json_albums:");
		for (Table.Row row : albums_json)
			System.out.println("  " + row.key() + " -> " + row.values());

		// reopen — verify name, columns, size, fingerprint survive disk round-trip
		JSONTable albums_json2 = new JSONTable("json_albums");
		System.out.println("\n=== json_albums (reopened) ===");
		System.out.println("name=" + albums_json2.name() + "  columns=" + albums_json2.columns());
		System.out.println("size=" + albums_json2.size() + "  fingerprints match: " + (albums_json.hashCode() == albums_json2.hashCode()));

		// -------------------------------------------------------------------------
		// JSONTable 2: Rock Albums
		// Same schema as json_albums — used for query method demonstration
		// -------------------------------------------------------------------------
		JSONTable rock_albums = new JSONTable("json_rock_albums", List.of("album", "artist", "year", "explicit"));
		rock_albums.put("OK Computer",   List.of("Radiohead",  1997, false));
		rock_albums.put("Nevermind",     List.of("Nirvana",    1991, false));
		rock_albums.put("Born to Run",   List.of("Springsteen", 1975, false));
		rock_albums.put("Led Zeppelin",  List.of("Led Zeppelin", 1969, false));
		System.out.println("\n=== json_rock_albums (new) ===");
		System.out.println(rock_albums);

		// reopen to verify persistence
		JSONTable rock_albums2 = new JSONTable("json_rock_albums");
		System.out.println("Reopened size=" + rock_albums2.size() + "  fingerprints match: " + (rock_albums.hashCode() == rock_albums2.hashCode()));

		// -------------------------------------------------------------------------
		// JSONTable 3: Hip-Hop Albums
		// Same schema — used for union/intersect/minus with json_albums
		// -------------------------------------------------------------------------
		JSONTable hiphop_albums = new JSONTable("json_hiphop_albums", List.of("album", "artist", "year", "explicit"));
		hiphop_albums.put("To Pimp a Butterfly", List.of("Kendrick",    2015, true));
		hiphop_albums.put("DAMN.",               List.of("Kendrick Lamar", 2017, true));
		hiphop_albums.put("My Beautiful Dark",   List.of("Kanye West",  2010, true));
		hiphop_albums.put("The Low End Theory",  List.of("A Tribe",     1991, false));
		System.out.println("\n=== json_hiphop_albums (new) ===");
		System.out.println(hiphop_albums);

		// reopen to verify persistence
		JSONTable hiphop_albums2 = new JSONTable("json_hiphop_albums");
		System.out.println("Reopened size=" + hiphop_albums2.size() + "  fingerprints match: " + (hiphop_albums.hashCode() == hiphop_albums2.hashCode()));

		// --- Query Methods ---

		// union: all albums from json_albums + json_hiphop_albums (no duplicate keys)
		QueryTable allAlbums = albums_json.union(hiphop_albums);
		System.out.println("\nunion json_albums ∪ json_hiphop_albums (size=" + allAlbums.size() + ", expected no duplicates):");
		System.out.println(allAlbums);

		// intersect: albums in json_albums whose key also exists in json_rock_albums
		QueryTable sharedRock = albums_json.intersect(rock_albums);
		System.out.println("intersect json_albums ∩ json_rock_albums (size=" + sharedRock.size() + "):");
		System.out.println(sharedRock);

		// minus: albums in json_albums that are NOT in json_rock_albums
		QueryTable nonRock = albums_json.minus(rock_albums);
		System.out.println("minus json_albums − json_rock_albums (size=" + nonRock.size() + "):");
		System.out.println(nonRock);
	}
}
