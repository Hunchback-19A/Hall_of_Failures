pscf_interaction_= \
  pscf/interaction/Interaction.cpp 

pscf_interaction_OBJS=\
     $(addprefix $(BLD_DIR)/, $(pscf_interaction_:.cpp=.o))

