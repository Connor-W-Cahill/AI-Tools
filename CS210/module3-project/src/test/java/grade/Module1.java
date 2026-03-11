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

@DisplayName("M1 Symbol Table")
@TestClassOrder(ClassOrderer.ClassName.class)
final class Module1 extends AbstractModule {
	@BeforeAll
	void defineModule() {
		containers = 3;
		operations = 100;
		elements = 13;
	}

	@Nested
	@DisplayName("m1_table1 [hit/miss only]")
	class Table1 extends SymbolTableContainer {
		@BeforeAll
		void defineTable() {
			name = "m1_table1";
			columns = List.of("name", "value");
			coverage = TestCoverage.HIT_MISS_ONLY;
		}
	}

	@Nested
	@DisplayName("m1_table2 [hit/miss, fingerprint]")
	class Table2 extends SymbolTableContainer {
		@BeforeAll
		void defineTable() {
			name = "m1_table2";
			columns = List.of("pair", "valueX", "valueY");
			coverage = TestCoverage.HM_FINGERPRINT;
		}
	}

	@Nested
	@DisplayName("m1_table3 [hit/miss, fingerprint, iterator]")
	class Table3 extends SymbolTableContainer {
		@BeforeAll
		void defineTable() {
			name = "m1_table3";
			columns = List.of("head", "tail1", "tail2", "tail3");
			coverage = TestCoverage.HM_FP_ITERATOR;
		}
	}

	abstract class SymbolTableContainer extends AbstractTableContainer {
		static final List<String> exempt = List.of(
    		"features",
			"tables",
			"java.lang.String",
			"java.lang.Number",
        	"java.lang.Boolean",
			"java.util.ImmutableCollections$AbstractImmutableCollection"
		);

		@Override
		String key() {
			return c();
		}

		@TestFactory
		@DisplayName("New Symbol Table")
		Stream<DynamicTest> testNewTable() {
			logStart("new");

			subject = testConstructor(
				"tables.SymbolTable",
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
						return testPut(false, CapacityProperty.NONE);
					else if (control.size() > elements * 1.01)
						return testRemove(true, CapacityProperty.NONE);
					else if (RNG.nextBoolean())
						return testGet(RNG.nextBoolean());
					else if (RNG.nextBoolean())
						return testPut(RNG.nextBoolean(), CapacityProperty.NONE);
					else
						return testRemove(RNG.nextBoolean(), CapacityProperty.NONE);
				}
			});
		}
	}
}