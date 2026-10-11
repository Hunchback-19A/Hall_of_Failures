/*
* PSCF - Polymer Self-Consistent Field
*
* Copyright 2015 - 2025, The Regents of the University of Minnesota
* Distributed under the terms of the GNU General Public License.
*/

#include "CFields.h"              // class header
#include <rpc/field/FieldIo.h>
#include <rp/field/CFields.tpp>   // base class implementation

// Explicit instantiation definitions
namespace Pscf {
   namespace Rp {
      using namespace Prdc;
      template class CFields<1, Cpu::RField<1>, Rpc::FieldIo<1> >;
      template class CFields<2, Cpu::RField<2>, Rpc::FieldIo<2> >;
      template class CFields<3, Cpu::RField<3>, Rpc::FieldIo<3> >;
   }
   namespace Rpc {
      template class CFields<1>;
      template class CFields<2>;
      template class CFields<3>;
   }
}
