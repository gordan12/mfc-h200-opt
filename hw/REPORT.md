# MFC 在 NVIDIA H200 上的 GPU 效能優化報告

> 分支 `opt`（最終版本 `fd1d0046`），基準為上游 MFC master `c3d6d176`。
> 環境：國網中心 nano4，1× NVIDIA H200，NVHPC 26.3（OpenACC），HPC-X MPI。

## 1. 摘要

| Benchmark | master（上游開源版） | 本作 `opt` | 加速 | 輸出 |
|---|---|---|---|---|
| `viscous_weno5_sgb_acoustic`（主 benchmark） | 0.738 ns/gp/eq/rhs | **0.3337** | **2.21×** | 與 master **逐位元相同**（46/46 檔 md5 一致） |
| `examples/3D_performance_test`（上游官方效能測例） | 0.330 | **0.2403–0.2410** | **1.37×** | 在 golden 容許誤差內（動量 ~1e-15） |

- 全部 19 個 commit 都保持數值正確。MFC 完整回歸測試在最終版 `fd1d0046` 上 **649/649 通過**。
- 同一次執行下，nsys 量到的 GPU kernel 總時間從 2761.6 ms 降到 1267.4 ms。每個 stage 的 kernel 數從 65 種降到 28 種。
- 主 benchmark 上，除了 `3D_performance_test` 那一點浮點重排外，所有優化都不改變任何一個位元。也就是說，這是**純粹的軟體效率提升，沒有拿精度換速度**。

## 2. Benchmark 與量測方法

### 2.1 Benchmark 選擇

主 benchmark 是 `benchmarks/viscous_weno5_sgb_acoustic`。它是上游 MFC 自帶的 benchmark 之一，物理模組最多：

- 5 方程模型（`model_eqns=2`），單流體 + Euler-Euler 氣泡（`bubbles_euler`、`bubble_model=3`、`nb=1`）
- WENO5 + mapped WENO + MP-WENO 單調性保持，HLLC Riemann solver（`riemann_solver=2`）
- 黏性項（`viscous=T`，有限差分梯度，`weno_Re_flux=F`），聲源（acoustic source）
- RK3 時間積分，`--gbpp 16`（每 GPU 約 16 GB 問題規模），網格約 316×158×158

另外用上游的 `examples/3D_performance_test`（無黏性）做第二個測例，確認優化不只對單一案例有效。

### 2.2 指標

- 指標是 MFC 自己輸出的 **grind time**（ns / 格點 / 方程 / RHS 評估），越小越好。
- 每個版本至少跑兩次（`-1g`、`-1g-b`），兩次差距都在 0.1% 以內。
- 另外各有一次 nsys（kernel 時間分佈）和 ncu（register、occupancy、記憶體流量、FP64 pipe）的 profile。

### 2.3 正確性驗證

- `hw/run.sh` 跑完後，對所有輸出檔（`p_all`、`D`、`restart_data`、`silo_hdf5`）算 md5，再和 master 的 md5 比對。主 benchmark 每一個版本都是 `SAME`。
- 重要節點另外跑 MFC 完整回歸測試（`./mfc.sh test`，649 個測例），結果如下：

  | commit | 結果 |
  |---|---|
  | `051bc8d8` | 649/649 |
  | `c519efd3` | 649/649 |
  | `fd1d0046` | 649/649 |

### 2.4 工具（`hw/`）

| 檔案 | 用途 |
|---|---|
| `env.sh` | NVHPC 26.3 / HPC-X 環境（含 `OPAL_PREFIX`，避免 srun 無法 `MPI_Init`） |
| `run.sh` | case-optimized build，在 node-local `/tmp` 執行，寫出 `results/<tag>/`（run.log、out.md5、commit） |
| `exp.sbatch` / `combo.sbatch` | 單一實驗；兩個 benchmark ×2 再加 nsys |
| `ncu.sbatch`、`tools/ncusum.py` | 只收 metric 的 ncu 與 roofline 摘要 |
| `test.sbatch` | 完整回歸測試（srun→mpirun shim） |
| `w1.sbatch`、`h1.sbatch` | 逐檔 register 上限掃描 |

量測時發現一個陷阱：2026-11-08 有幾個節點（hgpn006/007/009）因為資源競爭，所有程式都慢了約 5 倍。表 7 的 `e7-1g` 3.19 ns 就是這個原因造成的假象，換節點重跑（`e7r`）得到 0.600 ns。之後每次實驗都記錄 node load 與 `nvidia-smi`，並排除可疑節點。

## 3. 基準剖析（master）

master 的 nsys kernel 時間分佈如下（同一次執行、同樣步數）：

| 模組 | 時間 (ms) | 佔比 |
|---|---|---|
| HLLC Riemann solver | 771.5 | 27.9% |
| WENO 重建 | 537.2 | 19.5% |
| `s_get_viscous`（面梯度，18 個 kernel） | 372.9 | 13.5% |
| MP-WENO 單調性保持（獨立 pass） | 331.2 | 12.0% |
| 黏性 source flux | 279.3 | 10.1% |
| advection source | 97.7 | 3.5% |
| 氣泡 source | 90.4 | 3.3% |
| RK 更新 | 66.4 | 2.4% |
| 變數轉換 | 57.5 | 2.1% |
| 其他 | 約 157 | 約 5.7% |
| **總計** | **2761.6** | 65 個 kernel |

從 ncu 與 nsys 看出的主要問題：

1. **NVHPC 跨檔 inlining 失效**：
   - HLLC kernel 內的 EOS、混合物係數、聲速、Keller-Miksis 函式都變成真正的函式呼叫，register 要經由 stack 存取，造成大量 local memory 流量。
   - 原因有三個：
     - (a) `m_eos` 裡狀態相依 EOS 的呼叫鏈即使是 dead code，也會阻擋 inlining。
     - (b) `-Minline totalsize` 的預算在 x 方向的 HLLC kernel 就用完了，y、z 方向全部變成呼叫。
     - (c) 帶 optional 參數的 elemental 函式（`f_approx_equal`、`f_is_default`）無法跨檔 inline。
2. **主要 kernel 的 register 過多**：WENO、HLLC、黏性 flux 都用到 200 個以上，occupancy 只有 12.5%。
3. **多餘的 pass**：MP-WENO 單調性保持另開一個 pass，重讀所有面值。面梯度拆成 18 個小 kernel。還有好幾個清零或累加的 kernel。
4. **CPU 端同步**：每個 kernel 結束都做 `cuStreamSynchronize`，GPU 有 8.1% 的時間閒置。

## 4. 優化項目

下表的 ns 都是主 benchmark 的 grind time。每一步都是獨立的 commit，輸出逐位元相同。

| # | commit | 內容 | 前 → 後 (ns) |
|---|---|---|---|
| E2a-c | `32c1e993` | 恢復 NVHPC 跨檔 inlining：移除 dead EOS 呼叫鏈、提高 `-Minline totalsize`、HLLC 方向參數在編譯期決定 | 0.738 → 0.699 |
| E2d | `d992dde2` | 不做函式呼叫的能量與 Keller-Miksis helper，HLLC 不再重算混合物係數 | 0.699 → 0.694 |
| E6 | `2917d42e` | OpenACC compute region 改成非同步（`MFC_ACC_ASYNC`），GPU 閒置從 8.1% 降到 1.0% | 0.694 → 0.681 |
| E3 | `08ed93c6` | MP-WENO 單調性 bound 融合進 WENO5 kernel，在 register 內完成，只寫一次；共用的 minmod 只算一次 | → 0.632（與 E6 合併後 0.619） |
| E5b | `eae1bc19` | `s_get_viscous` 的 18 個面梯度 kernel 融合成 2 個 | 0.619 → 0.614 |
| E7 | `5924bd19` | 黏性 source flux 在 fypp 階段依 `norm_dir` 與是否 non-Newtonian 特化成 6 份，消除 1 GB/呼叫的 local memory 流量 | 0.614 → 0.600 |
| E9 | `69bdc02f` | 把氣泡壁壓力與 Keller-Miksis 函式 inline 進 kernel | 0.600 → 0.578 |
| E9b | `88a839b3` | 用 inline 運算式取代 `f_bub_is_dflt` helper；HLLC 的 register 從 232 降到 208，local 流量從 3.4 GB 降到 1.9 GB | 0.578 → 0.553 |
| MR | `051bc8d8` | 全域 register 上限 128（`MFC_GPU_MAXREG`），occupancy 從 12.5% 提高到 25% | 0.553 → **0.4518** |
| V1 | `9169842f` | 有限差分面梯度滿足 `dqR(j) ≡ dqL(j+1)`（同一個面上的同一個運算式），所以只算 dqL | 0.4518 → 0.4002 |
| V2 | `46512d0c` | 跨面平均改在 Riemann 黏性 flux 內現算，刪掉一個 kernel 和 6 個輸出陣列 | 0.4002 → 0.3735 |
| V3 | `c519efd3` | 直角座標不需要 cell-center 梯度（只有圓柱座標的軸上應力會用到），不再計算 | 0.3735 → 0.3575 |
| V4 | `57faf02e` | 黏性 flux 是 `flux_src(mom,E)` 的第一個寫入者，所以直接 store；省掉清零 kernel 和讀回 | 0.3575 → 0.3383 |
| V5 | `fd1d0046` | 黏性通量差 `(flux_src(j-1)-flux_src(j))/dx` 併進 advection kernel，每個方向少一次 rhs 的 read-modify-write | 0.3383 → **0.3337** |

### 4.1 關鍵技術細節

**跨檔 inlining（E2、E9）**

NVHPC 只有在函式體不呼叫任何其他程序時，才會跨檔 inline。上游程式碼因為一些「看起來無害」的寫法而無法 inline，包括 optional 參數、elemental helper 和 dead branch 裡的呼叫。結果是 HLLC kernel 內出現真正的 `call`，register 經由 local memory 存取。修正方式是逐一改寫成不呼叫其他程序的形式，然後用 ncu 確認 local 流量確實下降。

**Register 上限（MR）**

- 全域 register 上限掃描結果如下，128 最好：

  | 上限 | 96 | 112 | 128 | 168 |
  |---|---|---|---|---|
  | grind time (ns) | 0.502 | 0.503 | **0.4855** | 0.506 |

- 128 讓 occupancy 加倍，多出來的少量 spill 被 latency hiding 抵消。
- 在 `3D_performance_test` 上，這一項也讓 grind time 從 0.286 降到 0.240。

**逐位元等價的冗餘消除（V1–V5）**

這一組的核心觀察是：

- 有限差分面梯度 `dqL(j+1)` 和 `dqR(j)` 是同一個面上的同一個運算式，所以逐位元相同。
- 呼叫 Riemann solver 時 L、R 是對調的，消費端計算 `0.5*(a+a) == a` 在浮點下完全精確。

因此可以只算一份、只存一份，再把後續的平均、清零、累加、通量差一路往下游融合。每一步都保持相同的運算順序，所以輸出不變。

每個改動都受一個執行期旗標保護，旗標只在條件成立時開啟（直角座標、HLL/HLLC、無熱傳導、無 species diffusion、無 hypoelasticity 等）。其他物理組合照舊走原本的路徑，所以 649 個回歸測例全部通過。

| 旗標 | 位置 | 對應改動 |
|---|---|---|
| `shared_face_grad` | `m_global_parameters` | V1、V2 |
| `visc_src_store` | `m_global_parameters` | V4 |
| `visc_rhs_fused` | `m_rhs` | V5 |

## 5. 最終結果

### 5.1 Grind time 演進

```
master   0.738  ████████████████████████████████████  1.00×
E2a-c    0.699  ██████████████████████████████████    1.06×
E3+E6    0.619  ██████████████████████████████        1.19×
E7       0.600  █████████████████████████████         1.23×
E9b      0.553  ███████████████████████████           1.33×
MR128    0.452  ██████████████████████                1.63×
V1       0.400  ███████████████████                   1.84×
V2       0.374  ██████████████████                    1.98×
V3       0.357  █████████████████                     2.06×
V4       0.338  ████████████████                      2.18×
V5       0.334  ████████████████                      2.21×
```

`3D_performance_test` 的演進是 0.330 → 0.286（E2–E6）→ 0.240（MR）→ 0.241（V1–V5 不影響無黏性案例）。最終為 **1.37×**。

### 5.2 Kernel 時間分佈：master vs. 最終版

| 模組 | master (ms) | 最終 (ms) | 變化 |
|---|---|---|---|
| HLLC Riemann solver | 771.5 | 282.6 | **−63%** |
| WENO（含 MP-WENO） | 537.2 + 331.2 + 26.0 = 894.4 | 487.6 | **−45%** |
| 黏性：面梯度 `s_get_viscous` | 372.9 | 41.0 | **−89%** |
| 黏性：source flux | 279.3 | 79.5 | **−72%** |
| advection（含融合進來的黏性通量差） + additional physics | 97.7 + 45.1 | 126.3 | −12% |
| 氣泡 source | 90.4 | 49.6 | −45% |
| RK 更新 | 66.4 | 67.0 | 0% |
| 變數轉換 | 57.5 | 48.9 | −15% |
| **總計** | **2761.6** | **1267.4** | **−54%（2.18×）** |

最終版中 WENO 佔 38.5%，HLLC 佔 22.3%，兩者合計超過六成，是剩下的主要瓶頸。

## 6. 硬體極限分析

| Kernel | 限制因素（ncu） | 說明 |
|---|---|---|
| WENO5 | **FP64 指令發射** | FP64 pipe 使用率約 45%。每個變數約 700 條指令，含 13 個倒數，本質上是算術密集。DRAM 流量不是瓶頸。 |
| HLLC | **L1 latency** | register 128 時 occupancy 25%。再提高上限會降低 occupancy，降低上限則無法連結。 |
| RK、變數轉換、advection | **DRAM 頻寬** | 屬於 stream 型 kernel，合計只佔約 19%。額外成本主要是 Fortran derived type descriptor 的間接存取（RK kernel 每個元素 56 次 LDG，其中只有 3 次是資料）。 |

要再往上突破，需要**改變數值運算順序**（不再逐位元相同，但仍在容許誤差內），例如：

- WENO 權重的代數化簡，減少倒數；
- 混合精度。

本作刻意維持逐位元相同，所以沒有採用這些方法，列為未來工作。

## 7. 沒有效果的實驗（負面結果）

| 實驗 | 內容 | 結果 (ns) | 結論 |
|---|---|---|---|
| E8 | WENO 內部運算重排 | 0.5998（對照 0.5997） | 沒有收益，放棄 |
| E10 / E10b | 黏性梯度的另外兩種 kernel 切法 | 0.4625 / 0.4673（對照 0.4518） | 比較慢，放棄 |
| W1 | 只對 WENO 檔設 register 上限 80 / 96 / 168 / 255 | 0.474 / 0.457 / 0.454 / 0.490（對照 0.4518） | 全域 128 最好 |
| W2 | WENO 輸入打包成連續陣列 | 0.4547 | 打包成本抵消收益 |
| H1 | HLLC 單獨設 168 register | 0.4064（對照 0.4002） | occupancy 下降，比較慢 |
| H1 | HLLC 單獨設 96 / 112 register | 無法連結 | nvlink 不允許 caller 上限低於跨檔 callee 的 128 |
| T1 | RK kernel 讓每個 thread 處理多格 | 0.3991（對照 0.4002） | 只快 0.25%，descriptor 存取無法被提出迴圈 |
| e7（初版） | 黏性 flux 特化，在問題節點上量測 | 3.19 | 節點競爭造成的假象；換節點重跑（e7r）為 0.600 |

## 8. 與開源版本比較

- 比較對象是上游 MFC master `c3d6d176`。它是目前公開的最新開源版本，已包含官方的 OpenACC GPU 最佳化。
- 在同一張 H200、同一個編譯器、同一個 benchmark 下，本作快 2.21×（主 benchmark）與 1.37×（官方 performance test），輸出逐位元相同。
- 所有改動都限定在原本的程式架構（Fortran/fypp + OpenACC）內，沒有引入新的相依套件。不支援的組合會自動退回原本的路徑。

## 9. 重現方式

```bash
cd /work/your_user/mfc-opt && git checkout opt
cd hw
sbatch -w <idle node> combo.sbatch mytag   # 兩個 benchmark 各跑兩次，再加 nsys
cat results/mytag-1g/run.log | grep Performance
diff results/mytag-1g/out.md5 results/base-1g/out.md5   # 驗證逐位元一致
sbatch -t 04:00:00 test.sbatch                          # 完整回歸測試
```

`-DMFC_GPU_MAXREG=0` 可恢復編譯器預設的 register 配置。所有原始實驗數據都在 `hw/results/<tag>/`（run.log、out.md5、nsys、ncu）。

## 10. 結論

- 主 benchmark 從 0.738 降到 0.334 ns/gp/eq/rhs（**2.21×**），官方 performance test 快 **1.37×**。輸出與上游逐位元相同，回歸測試 649/649 通過。
- 效益主要有三個來源：
  - 恢復編譯器 inlining，加上控制 register 數；
  - 融合 kernel；
  - 利用逐位元恆等式消除重複計算與多餘的記憶體 pass。
- 剩下的時間由 WENO（FP64 發射）與 HLLC（L1 latency）主導，兩者在不改變數值結果的前提下已接近此架構的實際上限。
