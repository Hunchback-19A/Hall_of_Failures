/*
* PSCF - Polymer Self-Consistent Field
*
* Copyright 2015 - 2025, The Regents of the University of Minnesota
* Distributed under the terms of the GNU General Public License.
*/

#include "Domain.h"                 // class header
#include <rpc/field/FieldIo.tpp>    // base class template argument
#include <prdc/cpu/WaveList.h>      // base class template argument
#include <prdc/cpu/FFT.h>           // base class template argument
#include <rp/field/Domain.tpp>      // base class template implementation

// Explicit instantiation definitions
namespace Pscf {
   namespace Rp {
      using namespace Prdc::Cpu;
      template class Domain<1, FFT<1>, WaveList<1>, Rpc::FieldIo<1> >;
      template class Domain<2, FFT<2>, WaveList<2>, Rpc::FieldIo<2> >;
      template class Domain<3, FFT<3>, WaveList<3>, Rpc::FieldIo<3> >;
   }
   namespace Rpc {
      template class Domain<1>;
      template class Domain<2>;
      template class Domain<3>;
   }
}
