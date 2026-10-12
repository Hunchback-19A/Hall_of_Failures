/*
* PSCF - MixtureModifier Self-Consistent Field Theory
*
* Copyright 2015 - 2025, The Regents of the University of Minnesota
* Distributed under the terms of the GNU General Public License.
*/

#include "MixtureModifier.h"
#include <rp/solvers/MixtureModifier.tpp>
#include <rpc/solvers/Polymer.h>
#include <rpc/solvers/Solvent.h>
#include <rpc/solvers/Block.h>

namespace Pscf {
   namespace Rp { 
      template class MixtureModifier< Rpc::Mixture<1> >;
      template class MixtureModifier< Rpc::Mixture<2> >;
      template class MixtureModifier< Rpc::Mixture<3> >;
   }
   namespace Rpc { 
      template class MixtureModifier<1>;
      template class MixtureModifier<2>;
      template class MixtureModifier<3>;
   }
}
