package grade;

import static grade.Config.RANDOM_SEED;
import static org.junit.jupiter.api.AssertionFailureBuilder.assertionFailure;
import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.DynamicTest.dynamicTest;

import java.io.IOException;
import java.io.PrintStream;
import java.lang.invoke.MethodType;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Modifier;
import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedList;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.StringJoiner;

import org.jspecify.annotations.Nullable;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.TestInstance;
import org.junit.jupiter.api.TestInstance.Lifecycle;

import features.DataTable;
import features.Table;

enum TestCoverage {
	HIT_MISS_ONLY,
	HM_FINGERPRINT,
	HM_FP_ITERATOR
}

enum CapacityProperty {
	NONE,
	POWER_OF_TWO,
	CONGRUENT_PRIME,
	ANY
}

@TestInstance(Lifecycle.PER_CLASS)
abstract class AbstractModule {
	int containers, operations, elements;
	int runs, passes;

	@BeforeAll
	void startGrade() {
		runs = 0;
		passes = 0;
	}

	@AfterAll
	void reportGrade() {
		Class<?> container = this.getClass();
		var module = container.getSimpleName();
		while (container.getEnclosingClass() != null) {
			container = container.getEnclosingClass();
			module = "%s.%s".formatted(container.getSimpleName(), module);
		}

		var quota = containers * operations;
		var skips = quota - runs;
		var percent = (int) Math.ceil(passes / (double) quota * 100);

		System.out.printf("%s\n", module);
		System.out.printf("Tests: %,d", quota).println();
		if (skips == 0) {
			System.out.printf("Passing: %,d (%d%%)\n\n", passes, percent);
		}
		else {
			System.out.printf("Passing: %,d\n", passes);
			System.out.printf("Skipped: %,d (warning)\n\n", skips);
		}
	}

	@TestInstance(Lifecycle.PER_CLASS)
	abstract class AbstractTableContainer {
		String name;
		List<String> columns;

		Table subject;
		ControlTable control;
		List<String> keyCache;

		TestCoverage coverage;

		Random RNG;
		PrintStream log;

		@BeforeAll
		void startRNG() {
			if (RANDOM_SEED != null)
				RNG = new Random(RANDOM_SEED);
			else
				RNG = new Random();
		}

		Table testConstructor(String which, List<Class<?>> types, List<Object> params, List<String> exempt) {
			Table instance = null;
			try {
				var clazz = Class.forName(which);
				var ctor = clazz.getConstructor(types.toArray(new Class<?>[0]));

				instance = (Table) ctor.newInstance(params.toArray(new Object[0]));
				logConstructor(name, instance.getClass().getSimpleName(), enlist(params, false));
				keyCache = new LinkedList<>();

				thenTestForbiddenClasses(instance, exempt);
			}
			catch (InvocationTargetException e) {
				var cause = e.getCause();
				if (cause instanceof RuntimeException recause)
					throw recause;
				else
					throw new RuntimeException(cause);
			}
			catch (ClassNotFoundException | InstantiationException | IllegalAccessException | NoSuchMethodException e) {
				fail("Missing %d-parameter constructor with (%s) types for class %s".formatted(
					types.size(),
					enlist(types, false),
					which
				));
			}
			return instance;
		}

		void thenTestForbiddenClasses(Table table, List<String> exempt) {
			var fields = new HashSet<Field>();
			Collections.addAll(fields, table.getClass().getFields());
			Collections.addAll(fields, table.getClass().getDeclaredFields());

			testing:
			for (var field: fields) {
				field.setAccessible(true);

				if (Modifier.isVolatile(field.getModifiers()) && field.getName().startsWith("$"))
					continue testing;

				Object value = null;
				try {
					value = field.get(table);
				}
				catch (IllegalAccessException e) {
					fail("Unable to access fields to test forbidden classes");
				}

				if (value == null)
					continue testing;

				var type = value.getClass();
				while (type.isArray())
					type = type.getComponentType();

				if (type.isPrimitive())
					type = MethodType.methodType(type).wrap().returnType();

				var pname = type.getPackage().getName();
				for (var ename: exempt) {
					if (ename.equals(pname))
						continue testing;

					try {
						var eclass = Class.forName(ename);
						if (eclass.isAssignableFrom(type))
							continue testing;
					}
					catch (ClassNotFoundException e) {}
				}

				fail("Forbidden %s field named %s with %s value of type %s (review permitted fields)".formatted(
					Modifier.isStatic(field.getModifiers()) ? "static" : "instance",
					field.getName(),
					Modifier.isFinal(field.getModifiers()) ? "constant" : "variable",
					type.getName()
				));
			}
		}

		DynamicTest testClear() {
			var call = "clear()";
			logMethod(name, call);

			return dynamicTest(call, () -> {
				runs++;

				control.clear();
				keyCache.clear();

				subject.clear();

				thenTestSize("clear");
				thenTestFingerprint("clear");

				passes++;
			});
		}

		DynamicTest testPut(boolean collides, CapacityProperty property) {
			var key = key(collides);
			var values = values();
			var call = "put(%s, %s)".formatted(enquote(key), enlist(values, true));

			if (1 + values.size() == columns.size()) {
				logMethod(name, call);
				return dynamicTest(title(call, key), () -> {
					runs++;

					var expected = control.put(key, values);
					var hit = expected != null;

					if (hit)
						keyCache.remove(key);
					keyCache.addFirst(key);

					var actual = subject.put(key, values);

					if (hit) {
						assertNotNull(actual, "Should hit for key %s but missed".formatted(enquote(key)));

						assertListEquals(
							expected,
							actual,
							"Mismatched values for key %s on hit (data or type errors likely)".formatted(enquote(key))
						);
					}
					else {
						assertNull(actual, "Should miss for key %s but hit".formatted(enquote(key)));
					}

					thenTestSize("put");
					thenTestFingerprint("put");
					thenTestCapacityProperty("put", property);

					passes++;
				});
			}
			else {
				logMethodCommented(name, call);
				return dynamicTest("guarded " + title(call, key), () -> {
					runs++;

					assertThrows(IllegalArgumentException.class, () -> {
						subject.put(key, values);
					}, "Missing exception for values with size %d (guard condition error likely)".formatted(values.size()));

					passes++;
				});
			}
		}

		DynamicTest testGet(boolean collides) {
			var key = key(collides);
			var call = "get(%s)".formatted(enquote(key));
			logMethod(name, call);

			return dynamicTest(title(call, key), () -> {
				runs++;

				var expected = control.get(key);
				var hit = expected != null;

				var actual = subject.get(key);

				if (hit) {
					assertNotNull(actual, "Should hit for key %s but missed".formatted(enquote(key)));

					assertListEquals(
						expected,
						actual,
						"Mismatched values for key %s on hit (data or type errors likely)".formatted(enquote(key))
					);
				}
				else {
					assertNull(actual, "Should miss for key %s but hit".formatted(enquote(key)));
				}

				if (control.size() > 0)
					thenTestDegree("get");

				passes++;
			});
		}

		DynamicTest testRemove(boolean collides, CapacityProperty property) {
			var key = key(collides);
			var call = "remove(%s)".formatted(enquote(key));
			logMethod(name, call);

			return dynamicTest(title(call, key), () -> {
				runs++;

				var expected = control.remove(key);
				var hit = expected != null;

				if (hit)
					keyCache.remove(key);

				var actual = subject.remove(key);

				if (hit) {
					assertNotNull(actual, "Should hit for key %s but missed".formatted(enquote(key)));

					assertListEquals(
						expected,
						actual,
						"Mismatched values for key %s on hit (data or type errors likely)".formatted(enquote(key))
					);
				}
				else {
					assertNull(actual, "Should miss for key %s but hit".formatted(enquote(key)));
				}

				thenTestSize("remove");
				thenTestFingerprint("remove");
				thenTestCapacityProperty("remove", property);

				passes++;
			});
		}

		void thenTestDegree(String after) {
			var expected = columns.size();

			var actual = subject.degree();

			assertEquals(
				expected,
				actual,
				"After %s, degree off by %+d (calculation error likely)".formatted(after, actual - expected)
			);
		}

		void thenTestSize(String after) {
			var expected = control.size();

			var actual = subject.size();

			assertEquals(
				expected,
				actual,
				"After %s, size off by %+d (calculation error likely)".formatted(after, actual - expected)
			);
		}

		void thenTestCapacityProperty(String after, CapacityProperty property) {
			if (property == CapacityProperty.NONE)
				return;

			if (subject instanceof DataTable dsubject) {
				var capacity = dsubject.capacity();

				switch (property) {
					case NONE -> {}
					case POWER_OF_TWO -> assertTrue(
						isPowerOfTwo(capacity),
						"After %s, capacity %d not <a power of 2>".formatted(after, capacity)
					);
					case CONGRUENT_PRIME -> assertTrue(
						isCongruentPrime(capacity),
						"After %s, capacity %d not <a prime congruent to 3 modulo 4>".formatted(after, capacity)
					);
					case ANY -> assertTrue(
						isPowerOfTwo(capacity) || isCongruentPrime(capacity),
						"After %s, capacity %d neither <a power of 2> nor <a prime congruent to 3 modulo 4>".formatted(after, capacity)
					);
				}
			}
			else {
				fail("Table is not a data table (inheritance error likely)");
			}
		}

		boolean isPowerOfTwo(int capacity) {
			return capacity >= 2
				&& (capacity & (capacity - 1)) == 0;
		}

		boolean isCongruentPrime(int capacity) {
			return capacity >= 3
				&& capacity % 4 == 3
				&& BigInteger.valueOf(capacity).isProbablePrime(8);
		}

		void thenTestFingerprint(String after) {
			if (coverage.compareTo(TestCoverage.HM_FINGERPRINT) < 0)
				return;

			var expected = control.hashCode();

			var actual = subject.hashCode();

			assertEquals(
				expected,
				actual,
				"After %s, fingerprint off by %+d (corrupted rows likely)".formatted(after, actual - expected)
			);
		}

		DynamicTest testIterator() {
			var call = "iterator() traverses";

			return dynamicTest(call, () -> {
				runs++;

				var expected = control.size();

				var actual = 0;

				var iter = subject.iterator();
				assertNotNull(iter, "Null iterator");

				while (iter.hasNext()) {
					var row = iter.next();

					if (actual < expected) {
						assertNotNull(
							row,
							"Null row on iteration %d (hasNext/next errors likely)".formatted(actual)
						);

						if (!control.contains(row.key()))
							fail("Row with unknown key %s on iteration %d (hasNext/next errors likely)".formatted(enquote(row.key()), actual));

						assertListEquals(
							control.get(row.key()),
							row.values(),
							"Row with mismatched values for key %s on iteration %d (hasNext/next errors likely)".formatted(enquote(row.key()), actual)
						);
					}

					actual++;
				}

				assertEquals(
					expected,
					actual,
					"Iterations off by %+d (hasNext/next errors likely)".formatted(actual - expected)
				);

				passes++;
			});
		}

		DynamicTest testName() {
			var call = "name()";

			return dynamicTest(call, () -> {
				runs++;

				var expected = name;

				var actual = subject.name();

				assertEquals(
					expected,
					actual,
					"Mismatched name (assignment error likely)"
				);

				passes++;
			});
		}

		DynamicTest testColumns() {
			var call = "columns()";

			return dynamicTest(call, () -> {
				runs++;

				var expected = columns;

				var actual = subject.columns();

				assertListEquals(
					expected,
					actual,
					"Mismatched columns (assignment error likely)"
				);

				passes++;
			});
		}

		<T> void assertListEquals(@Nullable List<T> expected, @Nullable List<T> actual) {
			assertListEquals(expected, actual, (String) null);
		}

		<T> void assertListEquals(@Nullable List<T> expected, @Nullable List<T> actual, @Nullable String message) {
			if (expected == null ? actual != null : !expected.equals(actual)) {
				assertionFailure()
					.expected(enlist(expected, true))
					.actual(enlist(actual, true))
					.message(message)
					.buildAndThrow();
			}
		}

		String enquote(Object obj) {
			if (obj == null)
				return "null";
			else if (obj instanceof String)
				return "\"" + obj + "\"";
			else
				return obj.toString();
		}

		String enlist(List<?> elements, boolean wrapped) {
			StringJoiner sj;
			if (wrapped) {
				if (elements.stream().anyMatch(it -> it == null))
					sj = new StringJoiner(", ", "Arrays.asList(", ")");
				else
					sj = new StringJoiner(", ", "List.of(", ")");
			}
			else {
				sj = new StringJoiner(", ");
			}
			for (var element: elements) {
				if (element instanceof List<?> list)
					sj.add(enlist(list, true));
				else
					sj.add(enquote(element));
			}
			return sj.toString();
		}

		String title(String call, String key) {
			var hit = control.contains(key);
			return "%s on %s".formatted(
				hit ? "hit" : "miss",
				call
			);
		}

		String key(boolean collides) {
			if (collides && keyCache.size() >= 10) {
				int index;
				do {
					index = (int) (Math.abs(RNG.nextGaussian()) * 3);
				} while (index >= keyCache.size());
				return keyCache.get(index);
			}
			else {
				String k;
				do {
					k = key();
				} while (keyCache.contains(k));
				return k;
			}
		}

		String key() {
			var k = s();
			if (RNG.nextDouble() < .20) {
				var i = RNG.nextInt(TestData.MARK_BANK.length);
				var m = TestData.MARK_BANK[i];
				k = k + m + s();
			}
			return k;
		}

		String s() {
			var i = RNG.nextInt(TestData.WORD_BANK.length);
			var s = TestData.WORD_BANK[i];
			if (RNG.nextDouble() < .20) {
				if (RNG.nextBoolean())
					s = s.toUpperCase();
				else
					s = Character.toTitleCase(s.charAt(0)) + s.substring(1);
			}
			return s;
		}

		String c() {
			return s().substring(0, 1);
		}

		int i() {
			return (int) Math.clamp(RNG.nextGaussian() * 1000, -5000, +5000);
		}

		int ui() {
			return Math.abs(i());
		}

		Boolean b() {
			return RNG.nextBoolean();
		}

		List<Object> values() {
			var values = new LinkedList<>();
			var d = columns.size();
			if (RNG.nextDouble() < .01) {
				if (RNG.nextBoolean())
					d++;
				else
					d--;
			}
			for (var i = 1; i < d; i++) {
				var r = RNG.nextDouble();
				if (r < .60)
					values.add(s());
				else if (r < .90)
					values.add(i());
				else if (r < .99)
					values.add(b());
				else
					values.add(null);
			}
			return Collections.unmodifiableList(values);
		}

		void logStart(String suffix) {
			try {
				var path = Paths.get("db", "logs").resolve(suffix == null
					? "%s.java".formatted(name)
					: "%s_%s.java".formatted(name, suffix)
				);

				Files.createDirectories(path.getParent());
				log = new PrintStream(path.toFile());
			}
			catch (IOException e) {
				e.printStackTrace();
			}
		}

		void logLine(String line) {
			if (log != null)
				log.println(line);
		}

		void logConstructor(String refName, String className, String params) {
			if (log == null) return;

			logLine("Table %s = new %s(%s);".formatted(refName, className, params));
		}

		void logMethod(String name, String call) {
			if (log == null) return;

			logLine("%s.%s;".formatted(name, call));
		}

		void logMethodCommented(String reference, String call) {
			logMethod("// " + reference, call);
		}
	}
}

class ControlTable implements Table {
	public record ControlRow(String key, List<Object> values) {}

	Map<String, List<Object>> map;
	int fingerprint;

	ControlTable() {
		this.map = new HashMap<>(16);
	}

	@Override
	public void clear() {
		map.clear();
		fingerprint = 0;
	}

	@Override
	public List<Object> put(String key, List<Object> values) {
		var old = map.put(key, values);
		fingerprint += new ControlRow(key, values).hashCode();
		if (old != null) {
			fingerprint -= new ControlRow(key, old).hashCode();
			return old;
		}
		return null;
	}

	@Override
	public List<Object> remove(String key) {
		var old = map.remove(key);
		if (old != null) {
			fingerprint -= new ControlRow(key, old).hashCode();
			return old;
		}
		return null;
	}

	@Override
	public List<Object> get(String key) {
		return map.get(key);
	}

	@Override
	public boolean contains(String key) {
		return map.containsKey(key);
	}

	@Override
	public int degree() {
		throw new UnsupportedOperationException();
	}

	@Override
	public int size() {
		return map.size();
	}

	@Override
	public int hashCode() {
		return fingerprint;
	}

	@Override
	public Iterator<Row> iterator() {
		throw new UnsupportedOperationException();
	}

	@Override
	public String name() {
		throw new UnsupportedOperationException();
	}

	@Override
	public List<String> columns() {
		throw new UnsupportedOperationException();
	}
}

class TestData {
	static final String[] MARK_BANK = {
		"_", "__",
		"!", "?", ".",
		"@", "#", "$",
		"&", "|", "^", "~",
		"*", "/", "+", "-", "%", "="
	};

	/**
	 * Adapted from:
	 * https://simple.wikipedia.org/wiki/Wikipedia:List_of_1000_basic_words
	 */
	static final String[] WORD_BANK = {
		"true", "false", "null",
		"a", "about", "above", "across", "act", "active", "activity", "add", "afraid", "after", "again", "age", "ago", "agree", "air", "all", "alone", "along", "already", "always", "am", "amount", "an", "and", "angry", "another", "answer", "any", "anyone", "anything", "anytime", "appear", "apple", "are", "area", "arm", "army", "around", "arrive", "art", "as", "ask", "at", "attack", "aunt", "autumn", "away",
		"baby", "back", "bad", "bag", "ball", "bank", "base", "basket", "bath", "be", "bean", "bear", "beautiful", "bed", "bedroom", "beer", "behave",  "before", "begin", "behind", "bell", "below", "besides", "best", "better", "between", "big", "bird", "birth", "birthday", "bit", "bite", "black", "bleed", "block", "blood", "blow", "blue", "board", "boat", "body", "boil", "bone", "book", "border", "born", "borrow", "both", "bottle", "bottom", "bowl", "box", "boy", "branch", "brave", "bread", "break", "breakfast", "breathe", "bridge", "bright", "bring", "brother", "brown", "brush", "build", "burn", "business", "bus", "busy", "but",  "buy", "by",
		"cake", "call", "can", "candle", "cap", "car", "card", "care", "careful", "careless", "carry", "case", "cat", "catch",  "central", "century", "certain", "chair", "chance", "change", "chase", "cheap",  "cheese", "chicken", "child", "children", "chocolate", "choice", "choose", "circle", "city", "class", "clever", "clean", "clear", "climb", "clock", "cloth", "clothes", "cloud", "cloudy", "close", "coffee", "coat", "coin", "cold", "collect", "colour", "comb", "comfortable", "common", "compare", "come", "complete", "computer", "condition", "continue", "control", "cook", "cool", "copper", "corn", "corner", "correct", "cost", "contain", "count", "country", "course", "cover", "crash", "cross", "cry", "cup", "cupboard", "cut",
		"dance", "dangerous", "dark", "daughter", "day", "dead", "decide", "decrease", "deep", "deer", "depend", "desk", "destroy", "develop", "die", "different", "difficult", "dinner", "direction", "dirty", "discover", "dish", "do", "dog", "door", "double", "down", "draw", "dream", "dress", "drink", "drive", "drop", "dry", "duck", "dust", "duty",
		"each", "ear", "early", "earn", "earth", "east", "easy", "eat", "education", "effect", "egg", "eight", "either", "electric", "elephant", "else", "empty", "end", "enemy", "enjoy", "enough", "enter", "equal", "entrance", "escape", "even", "evening", "event", "ever", "every", "everyone", "exact", "everybody", "examination", "example", "except", "excited", "exercise", "expect", "expensive", "explain", "extremely", "eye",
		"face", "fact", "fail", "fall", "family", "famous", "far", "farm", "father", "fast", "fat", "fault", "fear", "feed", "feel", "female", "fever", "few", "fight", "fill", "film", "find", "fine", "finger", "finish", "fire", "first", "fish", "fit", "five", "fix", "flag", "flat", "float", "floor", "flour", "flower", "fly", "fold", "food", "fool", "foot", "football", "for", "force", "foreign", "forest", "forget", "forgive", "fork", "form", "fox", "four", "free", "freedom", "freeze", "fresh", "friend", "friendly", "from", "front", "fruit", "full", "fun", "funny", "furniture", "further", "future",
		"game", "garden", "gate", "general", "gentleman", "get", "gift", "give", "glad", "glass", "go", "goat", "god", "gold", "good", "goodbye", "grandfather", "grandmother", "grass", "grave", "great", "green", "gray", "ground", "group", "grow", "gun",
		"hair", "half", "hall", "hammer",  "hand", "happen", "happy", "hard", "hat", "hate", "have", "he", "head", "healthy", "hear", "heavy", "heart", "heaven", "height", "hello", "help", "hen", "her", "here", "hers", "hide", "high", "hill", "him", "his", "hit", "hobby", "hold", "hole", "holiday", "home", "hope", "horse", "hospital", "hot", "hotel", "house", "how", "hundred", "hungry", "hour", "hurry", "husband", "hurt",
		"I", "ice", "idea", "if", "important", "in", "increase", "inside", "into", "introduce", "invent", "iron", "invite", "is", "island", "it", "its",
		"jelly", "job", "join", "juice", "jump", "just",
		"keep", "key", "kill", "kind", "king", "kitchen", "knee", "knife", "knock", "know",
		"ladder", "lady", "lamp", "land", "large", "last", "late", "lately", "laugh", "lazy", "lead", "leaf", "learn", "leave", "leg", "left", "lend", "length", "less", "lesson", "let", "letter", "library", "lie", "life", "light", "like", "lion", "lip", "list", "listen", "little", "live", "lock", "lonely", "long", "look", "lose", "lot", "love", "low", "lower", "luck",
		"machine", "main", "make", "male", "man", "many", "map", "mark", "market", "marry", "matter", "may", "me", "meal", "mean", "measure", "meat", "medicine", "meet", "member", "mention", "method", "middle", "milk", "million", "mind", "minute", "miss", "mistake", "mix", "model", "modern", "moment", "money", "monkey", "month", "moon", "more", "morning", "most", "mother", "mountain", "mouth", "move", "much", "music", "must", "my",
		"name", "narrow", "nation", "nature", "near", "nearly", "neck", "need", "needle", "neighbour", "neither", "net", "never", "new", "news", "newspaper", "next", "nice", "night", "nine", "no", "noble", "noise", "none", "nor", "north", "nose", "not", "nothing", "notice", "now", "number",
		"obey", "object", "ocean", "of", "off", "offer", "office", "often", "oil", "old", "on", "one", "only", "open", "opposite", "or", "orange", "order", "other", "our", "out", "outside", "over", "own",
		"page", "pain", "paint", "pair", "pan", "paper", "parent", "park", "part", "partner", "party", "pass", "past", "path", "pay", "peace", "pen", "pencil", "people", "pepper", "per", "perfect", "period", "person", "petrol", "photograph", "piano", "pick", "picture", "piece", "pig", "pin", "pink", "place", "plane", "plant", "plastic", "plate", "play", "please", "pleased", "plenty", "pocket", "point", "poison", "police", "polite", "pool", "poor", "popular", "position", "possible", "potato", "pour", "power", "present", "press",  "pretty", "prevent", "price", "prince", "prison", "private", "prize", "probably", "problem", "produce", "promise", "proper", "protect", "provide", "public", "pull", "punish", "pupil", "push", "put",
		"queen", "question", "quick", "quiet", "quite",
		"radio", "rain", "rainy", "raise", "reach", "read", "ready", "real", "really", "receive", "record", "red", "remember", "remind", "remove", "rent", "repair", "repeat", "reply", "report", "rest", "restaurant", "result", "return", "rice", "rich", "ride", "right", "ring", "rise", "road", "rob", "rock", "room", "round", "rubber", "rude", "rule", "ruler", "run", "rush",
		"sad", "safe", "sail", "salt", "same", "sand", "save", "say", "school", "science", "scissors", "search", "seat", "second", "see", "seem", "sell", "send", "sentence", "serve", "seven", "several", "sex", "shade", "shadow", "shake", "shape", "share", "sharp", "she", "sheep", "sheet", "shelf", "shine", "ship", "shirt", "shoe", "shoot", "shop", "short", "should", "shoulder", "shout", "show", "sick", "side", "signal", "silence", "silly", "silver", "similar", "simple", "single", "since", "sing", "sink", "sister", "sit", "six", "size", "skill", "skin", "skirt", "sky", "sleep", "slip", "slow", "small", "smell", "smile", "smoke", "snow", "so", "soap", "sock", "soft", "some", "someone", "something", "sometimes", "son", "soon", "sorry", "sound", "soup", "south", "space", "speak", "special", "speed", "spell", "spend", "spoon", "sport", "spread", "spring", "square", "stamp", "stand", "star", "start", "station", "stay", "steal", "steam", "step", "still", "stomach", "stone", "stop", "store", "storm", "story", "strange", "street", "strong", "structure", "student", "study", "stupid", "subject", "substance", "successful", "such", "sudden", "sugar", "suitable", "summer", "sun", "sunny", "support", "sure", "surprise", "sweet", "swim", "sword",
		"table", "take", "talk", "tall", "taste", "taxi", "tea", "teach", "team", "tear", "telephone", "television", "tell", "ten", "tennis", "terrible", "test", "than", "that", "the", "their", "then", "there", "therefore", "these", "thick", "thin", "thing", "think", "third", "this", "though", "threat", "three", "tidy", "tie", "title", "to", "today", "toe", "together", "tomorrow", "tonight", "too", "tool", "tooth", "top", "total", "touch", "town", "train", "tram", "travel", "tree", "trouble", "trust", "twice", "try", "turn", "type",
		"ugly", "uncle", "under", "understand", "unit", "until", "up", "use", "useful", "usual", "usually",
		"vegetable", "very", "village", "voice", "visit",
		"wait", "wake", "walk", "want", "warm", "was", "wash", "waste", "watch", "water", "way", "we", "weak", "wear", "weather", "wedding", "week", "weight", "welcome", "were", "well", "west", "wet", "what", "wheel", "when", "where", "which", "while", "white", "who", "why", "wide", "wife", "wild", "will", "win", "wind", "window", "wine", "winter", "wire", "wise", "wish", "with", "without", "woman", "wonder", "word", "work", "world", "worry",
		"yard", "yell", "yesterday", "yet", "you", "young", "your",
		"zero", "zoo",
	};
}