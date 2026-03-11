package grade;

import java.util.List;
import java.util.stream.IntStream;
import java.util.stream.Stream;

import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.ClassOrderer;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.TestClassOrder;
import org.junit.jupiter.api.TestFactory;

@DisplayName("M2 Hash Table")
@TestClassOrder(ClassOrderer.ClassName.class)
final class Module2 extends AbstractModule {
	@BeforeAll
	void defineModule() {
		containers = 3;
		operations = 1000;
		elements = 500;
	}

	@Nested
	@DisplayName("m2_table1 [hit/miss only]")
	class Table1 extends HashTableContainer {
		@BeforeAll
		void defineTable() {
			name = "m2_table1";
			columns = List.of("k1", "f1a", "f1b");
			coverage = TestCoverage.HIT_MISS_ONLY;
		}
	}

	@Nested
	@DisplayName("m2_table2 [hit/miss, fingerprint]")
	class Table2 extends HashTableContainer {
		@BeforeAll
		void defineTable() {
			name = "m2_table2";
			columns = List.of("k2", "f2a", "f2b", "f2c");
			coverage = TestCoverage.HM_FINGERPRINT;
		}
	}

	@Nested
	@DisplayName("m2_table3 [hit/miss, fingerprint, iterator]")
	class Table3 extends HashTableContainer {
		@BeforeAll
		void defineTable() {
			name = "m2_table3";
			columns = List.of("k3", "f3a", "f3b", "f3c", "f3d", "f3e");
			coverage = TestCoverage.HM_FP_ITERATOR;
		}
	}

	abstract class HashTableContainer extends AbstractTableContainer {
		static final List<String> exempt = List.of(
    		"features",
			"tables",
			"java.lang.String",
			"java.lang.Number",
        	"java.lang.Boolean",
			"java.util.ImmutableCollections$AbstractImmutableCollection"
		);

		@TestFactory
		@DisplayName("New Hash Table")
		Stream<DynamicTest> testNewTable() {
			logStart("new");

			subject = testConstructor(
				"tables.HashTable",
				List.of(String.class, List.class),
				List.of(name, columns),
				exempt
			);

			control = new ControlTable();

			return IntStream.range(0, operations).mapToObj(i -> {
				if (i == 0)
					return testName();
				else if (i == 1)
					return testColumns();
				else if (i == 2 || i == operations-1)
					return testClear();
				else if ((i % 20 == 0 || i == operations-2) && coverage.compareTo(TestCoverage.HM_FP_ITERATOR) >= 0)
					return testIterator();
				else {
					if (control.size() < elements * .99)
						return testPut(false, CapacityProperty.ANY);
					else if (control.size() > elements * 1.01)
						return testRemove(true, CapacityProperty.NONE);
					else if (RNG.nextBoolean())
						return testGet(RNG.nextBoolean());
					else if (RNG.nextBoolean())
						return testPut(RNG.nextBoolean(), CapacityProperty.ANY);
					else
						return testRemove(RNG.nextBoolean(), CapacityProperty.NONE);
				}
			});
		}
	}
}