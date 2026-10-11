#ifndef PSCF_FH_MOLECULE_TEST_H
#define PSCF_FH_MOLECULE_TEST_H

#include <test/UnitTest.h>
#include <test/UnitTestRunner.h>

#include <pscf/floryHuggins/FhMolecule.h>
#include <util/misc/Log.h>

#include <fstream>

using namespace Pscf;
//using namespace Util;

class FhMoleculeTest : public UnitTest 
{

public:

   void setUp()
   {}

   void tearDown()
   {}

  
   void testConstructor()
   {
      printMethod(TEST_FUNC);
      FhMolecule molecule;
   } 

   void testReadWrite() {
      printMethod(TEST_FUNC);

      FhMolecule molecule;
      std::ifstream in;
      openInputFile("in/FhMolecule", in);

      molecule.readParam(in);
      TEST_ASSERT(molecule.nClump() == 2);
      TEST_ASSERT(molecule.clump(0).monomerId() == 0);
      TEST_ASSERT(eq(molecule.clump(0).size(), 2.0));
      TEST_ASSERT(molecule.clump(1).monomerId() == 1);
      TEST_ASSERT(eq(molecule.clump(1).size(), 3.0));
      TEST_ASSERT(eq(molecule.size(), 5.0));
      if (verbose() > 0) {
         printEndl();
         molecule.writeParam(Log::file());
      }
   }

   void testSetters()
   {
      printMethod(TEST_FUNC);
      FhMolecule molecule;

      molecule.setNClump(2);
      molecule.clump(0).setMonomerId(0);
      molecule.clump(0).setSize(2.0);
      molecule.clump(1).setMonomerId(1);
      molecule.clump(1).setSize(3.0);
      molecule.computeSize();

      TEST_ASSERT(molecule.nClump() == 2);
      TEST_ASSERT(molecule.clump(0).monomerId() == 0);
      TEST_ASSERT(eq(molecule.clump(0).size(), 2.0));
      TEST_ASSERT(molecule.clump(1).monomerId() == 1);
      TEST_ASSERT(eq(molecule.clump(1).size(), 3.0));
      TEST_ASSERT(eq(molecule.size(), 5.0));
   } 

};

TEST_BEGIN(FhMoleculeTest)
TEST_ADD(FhMoleculeTest, testConstructor)
TEST_ADD(FhMoleculeTest, testReadWrite)
TEST_ADD(FhMoleculeTest, testSetters)
TEST_END(FhMoleculeTest)

#endif
