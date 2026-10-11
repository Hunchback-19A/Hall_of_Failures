pscf_tests_interaction_=pscf/tests/interaction/Test.cpp

pscf_tests_interaction_OBJS=\
     $(addprefix $(BLD_DIR)/, $(pscf_tests_interaction_:.cpp=.o))

