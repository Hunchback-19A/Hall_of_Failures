#ifndef INTERACTION_TEST_H
#define INTERACTION_TEST_H

#include <test/UnitTest.h>
#include <test/UnitTestRunner.h>

#include <pscf/interaction/Interaction.h>
#include <util/param/BracketPolicy.h>

#include <fstream>

using namespace Pscf;
using namespace Util;

class InteractionTest : public UnitTest 
{

public:

   void setUp()
   {  BracketPolicy::set(BracketPolicy::Optional); }

   void tearDown()
   {}

  
   void testConstructor()
   {
      printMethod(TEST_FUNC);
      Interaction v;
      v.setNMonomer(2);
   } 

   void testReadWrite1() 
   {
      printMethod(TEST_FUNC);

      Interaction v;
      const int nMonomer = 2;
      v.setNMonomer(nMonomer);
      std::ifstream in;
      openInputFile("in/Interaction", in);

      v.readParam(in);
      if (verbose() > 0){
         printEndl();
         v.writeParam(std::cout);
      }

      TEST_ASSERT(eq(v.chi(0,0), 0.0));
      TEST_ASSERT(eq(v.chi(1,1), 0.0));
      TEST_ASSERT(eq(v.chi(0,1), 1.0));
      TEST_ASSERT(eq(v.chi(1,0), 1.0));
      TEST_ASSERT(eq(v.chi(1,0), v.chi(0,1)));

   }

   void testReadWrite2() 
   {
      printMethod(TEST_FUNC);

      Interaction v;
      const int nMonomer = 2;
      v.setNMonomer(nMonomer);
      std::ifstream in;
      openInputFile("in/Interaction2", in);

      v.readParam(in);
      if (verbose() > 0){
         printEndl();
         v.writeParam(std::cout);
      }

   }

   void testReadWrite3() 
   {
      printMethod(TEST_FUNC);

      Interaction v;
      const int nMonomer = 3;
      v.setNMonomer(nMonomer);
      std::ifstream in;
      openInputFile("in/Interaction3", in);

      v.readParam(in);
      if (verbose() > 0){
         printEndl();
         v.writeParam(std::cout);
      }

      TEST_ASSERT(eq(v.chi(1,0), v.chi(0,1)));
      TEST_ASSERT(eq(v.chi(1,2), v.chi(2,1)));
      TEST_ASSERT(eq(v.chi(0,2), v.chi(2,0)));

   }

};

TEST_BEGIN(InteractionTest)
TEST_ADD(InteractionTest, testConstructor)
TEST_ADD(InteractionTest, testReadWrite1)
TEST_ADD(InteractionTest, testReadWrite2)
TEST_ADD(InteractionTest, testReadWrite3)
TEST_END(InteractionTest)

#endif
