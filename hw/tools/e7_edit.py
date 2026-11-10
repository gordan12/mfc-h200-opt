"""E7: specialize s_compute_cartesian_viscous_source_flux on norm_dir and any_non_newtonian at fypp time.

The runtime norm_dir indexed the private 3x3 stress tensors (forcing them into local memory) and the
non-Newtonian path inflated the register count of every launch. Each of the six copies keeps the original
expressions, so results are bitwise identical.
"""
import re
import sys

p = sys.argv[1] + "/src/simulation/m_riemann_state.fpp"
s = open(p).read()

sub_a = s.index("    subroutine s_compute_cartesian_viscous_source_flux(")
sub_b = s.index("    end subroutine s_compute_cartesian_viscous_source_flux")
sub = s[sub_a:sub_b]
ka = sub.index("        $:GPU_PARALLEL_LOOP(collapse=3, private='[idx_right_phys")
kend = "        $:END_GPU_PARALLEL_LOOP()\n"
kb = sub.index(kend) + len(kend)
k = sub[ka:kb]

# 1. the three norm_dir branches selecting Re and the interface velocity are identical: keep one, NN at fypp time
ba = k.index("                    if (norm_dir == 1) then\n")
end_tok = "                    end if\n\n                    if (shear_stress) then"
bb = k.index(end_tok)
branch = k[ba:bb + len("                    end if\n")]
assert branch.count("Re_shear = Re_avg_rsx_vf(j_loop, k_loop, l_loop, 1)") == 3
single = """                    #:if NN
                        Re_shear = Re_nn(1)
                        Re_bulk = Re_nn(2)
                    #:else
                        Re_shear = Re_avg_rsx_vf(j_loop, k_loop, l_loop, 1)
                        Re_bulk = Re_avg_rsx_vf(j_loop, k_loop, l_loop, 2)
                    #:endif
                    do i_dim = 1, num_dims
                        vel_src_at_interface(i_dim) = vel_src_rsx_vf(j_loop, k_loop, l_loop, i_dim)
                    end do
"""
k = k[:ba] + single + k[bb + len("                    end if\n"):]

# 2. the non-Newtonian shear-rate block becomes fypp-conditional
nn_a = k.index("                    if (any_non_newtonian) then\n")
nn_end = "                        call s_compute_mixture_inv_re(alpha_avg, gamma_dot, Res_gs, Re_nn)\n                    end if\n"
nn_b = k.index(nn_end, nn_a) + len(nn_end)
blk = k[nn_a:nn_b]
inner = blk[len("                    if (any_non_newtonian) then\n"):-len("                    end if\n")]
inner = "".join(l[4:] if l.startswith("    ") else l for l in inner.splitlines(True))
k = k[:nn_a] + "                    #:if NN\n" + inner + "                    #:endif\n" + k[nn_b:]
assert "any_non_newtonian" not in k

# 3. norm_dir becomes the fypp constant ND
k = re.sub(r"\bnorm_dir\b", "${ND}$", k)


def indent(t, n):
    return "".join((" " * n + l) if l.strip() and not l.lstrip().startswith("#:") else
                   (l[:len(l) - len(l.lstrip())] + " " * n + l.lstrip()) if l.strip() else l
                   for l in t.splitlines(True))


body = "        #:for ND in [1, 2, 3]\n"
body += "            #:if not MFC_CASE_OPTIMIZATION or ND <= num_dims\n"
body += "                #:for NN in [True, False]\n"
body += "                    if (norm_dir == ${ND}$ .and. (any_non_newtonian .eqv. ${'.true.' if NN else '.false.'}$)) then\n"
body += indent(k, 12)
body += "                    end if\n"
body += "                #:endfor\n"
body += "            #:endif\n"
body += "        #:endfor\n"
sub = sub[:ka] + body + sub[kb:]
s = s[:sub_a] + sub + s[sub_b:]
open(p, "w").write(s)
print("ok")
