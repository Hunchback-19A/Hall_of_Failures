#ifndef PSCF_CORRELATION_TEST_COMPOSITE_H
#define PSCF_CORRELATION_TEST_COMPOSITE_H

#include <test/CompositeTestRunner.h>

#include "PolymerCorrelationTest.h"
#include "MixtureCorrelationTest.h"

TEST_COMPOSITE_BEGIN(CorrelationTestComposite)
TEST_COMPOSITE_ADD_UNIT(PolymerCorrelationTest);
TEST_COMPOSITE_ADD_UNIT(MixtureCorrelationTest);
TEST_COMPOSITE_END

#endif
