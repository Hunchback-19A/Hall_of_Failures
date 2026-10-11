#ifndef PSCF_FLORY_HUGGINS_TEST_COMPOSITE_H
#define PSCF_FLORY_HUGGINS_TEST_COMPOSITE_H

#include <test/CompositeTestRunner.h>

#include "FhClumpTest.h"
#include "FhMoleculeTest.h"
#include "FhInteractionTest.h"
#include "FhMixtureTest.h"

TEST_COMPOSITE_BEGIN(FloryHugginsTestComposite)
TEST_COMPOSITE_ADD_UNIT(FhClumpTest);
TEST_COMPOSITE_ADD_UNIT(FhMoleculeTest);
TEST_COMPOSITE_ADD_UNIT(FhInteractionTest);
TEST_COMPOSITE_ADD_UNIT(FhMixtureTest);
TEST_COMPOSITE_END

#endif
