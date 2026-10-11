#ifndef PSCF_FH_CLUMP_TEST_H
#define PSCF_FH_CLUMP_TEST_H

#include <test/UnitTest.h>
#include <test/UnitTestRunner.h>

#include <pscf/floryHuggins/FhClump.h>
#include <util/misc/Log.h>

#include <fstream>

using namespace Pscf;
using namespace Util;

class FhClumpTest : public UnitTest 
{

public:

   void setUp()
   {
      //setVerbose(1);
   }

   void tearDown()
   {}

  
   void testConstructor()
   {
      printMethod(TEST_FUNC);
      FhClump clump;
   } 

   void testSetters()
   {
      printMethod(TEST_FUNC);
      FhClump clump;
      clump.setMonomerId(0);
      clump.setSize(2.0);
      TEST_ASSERT(clump.monomerId() == 0);
      TEST_ASSERT(eq(clump.size(), 2.0));
   } 

   void testReadWrite() {
      printMethod(TEST_FUNC);

      FhClump clump;
      std::ifstream in;
      openInputFile("in/FhClump", in);

      in >> clump;
      TEST_ASSERT(clump.monomerId() == 0);
      TEST_ASSERT(eq(clump.size(), 2.0));
      if (verbose() > 0) {
         printEndl();
         Log::file() << clump << std::endl ;
      }
   }

};

TEST_BEGIN(FhClumpTest)
TEST_ADD(FhClumpTest, testConstructor)
TEST_ADD(FhClumpTest, testSetters)
TEST_ADD(FhClumpTest, testReadWrite)
TEST_END(FhClumpTest)

#endif
