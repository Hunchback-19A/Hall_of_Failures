pscf_tests_correlation_=pscf/tests/correlation/Test.cpp

pscf_tests_correlation_OBJS=\
     $(addprefix $(BLD_DIR)/, $(pscf_tests_correlation_:.cpp=.o))

