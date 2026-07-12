# 绗簩闂洃鐫ｉ娴嬩笌涓夌淮杞ㄨ抗寤烘ā鎵ц浠诲姟涔?

## 1. 椤圭洰鑼冨洿

椤圭洰浠撳簱锛?

```text
https://github.com/feiniao87968492/shixun2
```

鏈澶勭悊锛?

```text
questions/q2/
```

姝ｅ紡鍏ュ彛锛?

```bash
python questions/q2/scripts/pipeline.py \
  --config configs/default.yaml
```

褰撳墠绗簩闂粛澶勪簬 `planned` 鐘舵€侊紝姝ｅ紡鑴氭湰灏氭湭瀹炵幇銆傞鐩姹傞娴嬮琛岃窛绂诲拰鏈€楂樼偣楂樺害锛屽苟寤虹珛涓夌淮 ODE 妯″瀷瀹屾垚鍏稿瀷璁板綍璇樊鍒嗘瀽銆?

---

# 2. 鏈棶鏈€缁堢洰鏍?

绗簩闂繀椤诲悓鏃跺畬鎴愪袱绫绘ā鍨嬨€?

## 2.1 鐩戠潱棰勬祴妯″瀷

寤虹珛杈撳叆鍑荤悆鍙傛暟鍒颁互涓嬩袱涓洰鏍囩殑鏄犲皠锛?

[
f_D(X)=D_{\mathrm{carry}}
]

[
f_H(X)=H_{\max}
]

鍏朵腑锛?

* (D_{\mathrm{carry}})锛氶琛岃窛绂伙紱
* (H_{\max})锛氭渶楂樼偣楂樺害銆?

鎸夌収棰樼洰瑕佹眰锛?

* 70% 涓鸿缁冮泦锛?
* 30% 涓烘祴璇曢泦锛?
* 鎶ュ憡 RMSE锛?
* 鎶ュ憡 MAPE銆?

鍙﹀澧炲姞锛?

* MAE锛?
* (R^2)锛?
* 涓綅缁濆鐧惧垎姣旇宸?MdAPE锛?
* 娴嬭瘯闆?Bootstrap 缃俊鍖洪棿銆?

---

## 2.2 涓夌淮鍔ㄥ姏瀛︽ā鍨?

寤虹珛锛?

[
\frac{d\boldsymbol r}{dt}=\boldsymbol v
]

[
m\frac{d\boldsymbol v}{dt}
==========================

\boldsymbol F_g+
\boldsymbol F_D+
\boldsymbol F_L
]

妯″瀷杈撳嚭锛?

* 椋炶璺濈锛?
* 鏈€楂樼偣楂樺害锛?
* 妯悜鍋忕Щ锛?
* 椋炶鏃堕棿锛?
* 瀹屾暣涓夌淮杞ㄨ抗銆?

浣跨敤璁粌鏁版嵁浼拌绌烘皵闃诲姏鍜屽崌鍔涚浉鍏冲弬鏁帮紝鍦ㄦ祴璇曟暟鎹笂璇勪环銆?

---

# 3. 蹇呴』鍏堝鐞嗙殑浠撳簱闂

## 3.1 鍘熷鏁版嵁褰掓。涓嶄竴鑷?

`docs/data_dictionary.md` 澹扮О PDF銆丱CR 鏂囨湰鍜?Excel 宸插綊妗ｅ湪锛?

```text
data/raw/problem/
```

浣嗗叕寮€浠撳簱涓殑 `data/raw/` 鐩墠鍙湁 `.gitkeep`銆?

鏈湴 Agent 棣栧厛妫€鏌ユ湰鍦板伐浣滃尯鏄惁瀹為檯鍏锋湁锛?

```text
data/raw/problem/2026骞村疄璁2 楂樺皵澶悆椋炶杞ㄨ抗棰勬祴涓庢渶浼樺嚮鐞冪瓥鐣ュ缓妯?pdf
data/raw/problem/2026骞村疄璁2 楂樺皵澶悆椋炶杞ㄨ抗棰勬祴涓庢渶浼樺嚮鐞冪瓥鐣ュ缓妯?pdf_by_PaddleOCR-VL-1.6.md
data/raw/problem/闄勪欢锛堝疄璁2锛?xlsx
```

澶勭悊瑙勫垯锛?

* 鏈湴鏈夋枃浠讹細楠岃瘉鍝堝笇骞剁户缁紱
* 鏈湴娌℃湁鏂囦欢锛氳嚦灏戠‘璁?`data/processed/golf_shots_clean.csv` 瀛樺湪锛?
* 涓嶅緱鎶婇闈㈢粰鍑虹殑鐗╃悊甯告暟鍑蹇嗗啓鍏ヤ唬鐮侊紱
* 浠庨闈㈣鍙栬川閲忋€佺洿寰勩€佺┖姘斿瘑搴︺€侀噸鍔涘姞閫熷害绛夊父鏁帮紱
* 姣忎釜鐗╃悊甯告暟璁板綍棰橀潰椤电爜鎴栨潵婧愩€?

---

## 3.2 淇杩囨椂鐨勪笂娓镐緷璧?

褰撳墠 `manifest.yaml` 渚濊禆锛?

```text
questions/q1/artifacts/tables/q1_feature_importance.csv
```

璇ユ枃浠跺悕宸茬粡涓嶆槸绗竴闂綋鍓嶇殑鏈€缁堢粨璁哄叆鍙ｃ€?

鏇存柊涓哄疄闄呭瓨鍦ㄧ殑鏂囦欢锛岃嚦灏戝寘鎷細

```text
questions/q1/artifacts/tables/q1_feature_summary.csv
questions/q1/artifacts/tables/q1_data_audit.csv
questions/q1/artifacts/tables/q1_invalid_zero_records.csv
```

绗簩闂笉搴斾粎鏍规嵁绗竴闂帓鍚嶆満姊板垹闄ゅ彉閲忋€?

---

# 4. 鎬讳綋鎶€鏈矾绾?

鎸変互涓嬮『搴忓疄鏂斤細

```text
闃舵 A锛氭暟鎹帴鍙ｅ拰鍥哄畾娴嬭瘯闆?
闃舵 B锛氱洃鐫ｉ娴嬪熀绾?
闃舵 C锛氱洃鐫ｉ娴嬩富妯″瀷
闃舵 D锛歄DE 鍧愭爣銆佸崟浣嶅拰鍩虹嚎妯″瀷
闃舵 E锛氶樆鍔涗笌鍗囧姏鍙傛暟鏍囧畾
闃舵 F锛氭祴璇曢泦鍜屽吀鍨嬭褰曢獙璇?
闃舵 G锛氱伒鏁忓害銆佽瘖鏂拰鏂囨。
```

涓嶅緱鍏堢敾涓夌淮杞ㄨ抗锛屽啀鍙嶆帹鏂圭▼鍜屽弬鏁般€?

---

# 5. 鏁版嵁涓庣壒寰佸畾涔?

## 5.1 绂佹浣滀负杈撳叆鐨勫瓧娈?

浠ヤ笅瀛楁涓嶅緱鐢ㄤ簬鐩戠潱妯″瀷杈撳叆锛?

```text
sample_id / 搴忓彿
carry_distance_yd
apex_height_yd
total_distance_yd
lateral_offset_yd
```

鍏朵腑锛?

* 椋炶璺濈鍜屾渶楂樼偣楂樺害鏄洰鏍囷紱
* 鎬昏窛绂诲寘鍚惤鍦版粴鍔ㄤ俊鎭紱
* 妯悜鍋忕Щ鏄琛岀粨鏋滐紱
* 搴忓彿娌℃湁棰勬祴鎰忎箟銆?

---

## 5.2 涓荤壒寰侀泦锛歈3 鍏煎鍙戝皠鐘舵€?

涓绘ā鍨嬩娇鐢細

```text
ball_speed_mph
launch_angle_deg
launch_direction_deg
spin_rate_rpm
spin_axis_deg
```

鍘熷洜锛?

1. 杩欎簺鍙橀噺鎻忚堪鐞冪寮€鏉嗛潰鍚庣殑鍒濆鐘舵€侊紱
2. 涓嶅瓨鍦ㄦ潌澶撮€熷害銆佹敾鍑昏鐨勭己澶遍棶棰橈紱
3. 涓?ODE 鍒濆鏉′欢涓€鑷达紱
4. 绗笁闂彲浠ョ洿鎺ュ湪杩欎簺鍙橀噺涓婃悳绱㈡渶浼樺弬鏁般€?

璇ユā鍨嬪懡鍚嶄负锛?

```text
launch_state_model
```

---

## 5.3 鎵╁睍鐗瑰緛闆?

鐢ㄤ簬绮惧害姣旇緝锛?

```text
ball_speed_mph
launch_angle_deg
launch_direction_deg
spin_rate_rpm
spin_axis_deg
club_speed_mph
attack_angle_deg
```

鍛藉悕涓猴細

```text
full_shot_model
```

鏉嗗ご閫熷害鍜屾敾鍑昏锛?

* 纭寮傚父闆跺€肩户缁涓虹己澶憋紱
* 鎻掕ˉ蹇呴』鍦ㄨ缁冩祦姘寸嚎鍐呴儴瀹屾垚锛?
* 澧炲姞缂哄け鎸囩ず鍙橀噺锛?
* 涓嶅緱鍦ㄥ垝鍒嗘祴璇曢泦鍓嶅鍏ㄩ儴鏁版嵁鎻掕ˉ銆?

---

## 5.4 鑷棆琛ㄧず鏁忔劅鎬?

姣旇緝涓ょ鏂规锛?

### 鏂规 A

```text
spin_rate_rpm
spin_axis_deg
```

### 鏂规 B

```text
backspin_rpm
sidespin_rpm
```

鐩戠潱涓绘ā鍨嬩紭鍏堜繚鐣欐柟妗?A锛屽洜涓虹涓夐棶鏇村鏄撲紭鍖栨€昏嚜鏃嬪拰杞村亸瑙掋€?

鑻ユ柟妗?B 棰勬祴鏄庢樉鏇翠紭锛屽皢鍏朵綔涓虹簿搴︿笂闄愭ā鍨嬶紝浣嗕粛淇濈暀鏂规 A 浣滀负绗笁闂唬鐞嗘ā鍨嬨€?

---

# 6. 鍥哄畾璁粌娴嬭瘯鍒掑垎

棰樼洰瑕佹眰 70%/30%锛屽洜姝ゅ缓绔嬩竴涓浐瀹氫富鍒掑垎锛?

```python
train_test_split(
    data,
    test_size=0.30,
    random_state=2026
)
```

蹇呴』淇濆瓨鏍锋湰缂栧彿锛?

```text
questions/q2/artifacts/tables/q2_data_split.csv
```

瀛楁锛?

```text
sample_id
split
random_seed
```

鎵€鏈夌洃鐫ｆā鍨嬪拰 ODE 妯″瀷蹇呴』浣跨敤鍚屼竴涓诲垝鍒嗐€?

瑙勫垯锛?

* 瓒呭弬鏁板彧鑳戒娇鐢?70% 璁粌闆嗗唴閮ㄤ氦鍙夐獙璇侀€夋嫨锛?
* 30% 娴嬭瘯闆嗗彧鐢ㄤ簬鏈€缁堣瘎浠凤紱
* 涓嶅緱鏍规嵁娴嬭瘯闆嗚〃鐜板弽澶嶄慨鏀规ā鍨嬶紱
* 鍏稿瀷 100銆?50銆?00 yd 璁板綍浠庢祴璇曢泦閫夋嫨銆?

褰撳墠 `approach.md` 涓€滄渶灏忓寲娴嬭瘯 RMSE/MAPE鈥濈殑琛ㄨ堪搴旀敼涓衡€滆缁冮泦鍐呴儴閫夋嫨妯″瀷锛屾祴璇曢泦鍙繘琛屾渶缁堣瘎浠封€濄€?

---

# 7. 鐩戠潱棰勬祴妯″瀷

## 7.1 鍩虹嚎妯″瀷

蹇呴』鍖呭惈锛?

### Baseline 0锛氬潎鍊兼ā鍨?

```python
DummyRegressor(strategy="mean")
```

鐢ㄤ簬璇存槑妯″瀷鏄惁鐪熸瀛︿範鍒颁俊鎭€?

### Baseline 1锛氬鍏冪嚎鎬у洖褰?

```python
StandardScaler()
LinearRegression()
```

### Baseline 2锛氬箔鍥炲綊

```python
StandardScaler()
RidgeCV(...)
```

---

## 7.2 闈炵嚎鎬у€欓€夋ā鍨?

鍙娇鐢ㄥ皯閲忔湁浠ｈ〃鎬х殑妯″瀷锛?

```text
ExtraTreesRegressor
HistGradientBoostingRegressor
```

鍙€夊鍔狅細

```text
SVR
```

涓嶉渶瑕佸ぇ閲忓爢鍙犳ā鍨嬨€?

鍒嗗埆棰勬祴锛?

```text
carry_distance_yd
apex_height_yd
```

寤鸿涓轰袱涓洰鏍囧垎鍒€夋嫨鏈€浼樻ā鍨嬶紝鑰屼笉鏄己鍒朵娇鐢ㄥ悓涓€涓畻娉曘€?

---

## 7.3 妯″瀷閫夋嫨

鍦ㄨ缁冮泦涓婁娇鐢細

```text
5 鎶樹氦鍙夐獙璇?
```

鍊欓€夋ā鍨嬫瘮杈冿細

* CV RMSE锛?
* CV MAE锛?
* CV (R^2)锛?
* 璁粌鏃堕棿锛?
* 绋冲畾鎬с€?

妯″瀷閫夋嫨涓嶅緱渚濇嵁娴嬭瘯闆嗐€?

---

## 7.4 娴嬭瘯闆嗘寚鏍?

瀵规瘡涓洰鏍囥€佹瘡涓ā鍨嬭緭鍑猴細

[
\mathrm{RMSE}
=============

\sqrt{
\frac1n
\sum_{i=1}^{n}
(\hat y_i-y_i)^2
}
]

[
\mathrm{MAPE}
=============

\frac{100%}{n}
\sum_{i=1}^{n}
\left|
\frac{\hat y_i-y_i}{y_i}
\right|
]

鍚屾椂鎶ュ憡锛?

```text
MAE
R虏
MdAPE
```

鏈€楂樼偣楂樺害瀛樺湪杈冨皬鍊硷紝MAPE 鍙兘瀵逛綆楂樺害鏍锋湰鏁忔劅锛屽洜姝ゅ繀椤诲悓鏃舵姤鍛?MAE 鍜?MdAPE銆?

---

## 7.5 娴嬭瘯闆嗙疆淇″尯闂?

瀵瑰浐瀹氭祴璇曢泦棰勬祴缁撴灉杩涜 1000 娆℃牱鏈?Bootstrap锛屾姤鍛婏細

```text
RMSE 95% CI
MAPE 95% CI
MAE 95% CI
```

Bootstrap 鍙噸閲囨牱娴嬭瘯闆嗛娴嬪锛屼笉閲嶆柊璋冨弬銆?

---

## 7.6 棰勬祴璇婃柇

鐢熸垚锛?

1. 鐪熷疄鍊尖€旈娴嬪€兼暎鐐瑰浘锛?
2. 娈嬪樊鈥旈娴嬪€煎浘锛?
3. 娈嬪樊鍒嗗竷鍥撅紱
4. 娴嬭瘯鏍锋湰缁濆璇樊鎺掑簭琛紱
5. 鎸夌悆閫熴€佸彂灏勮銆佽嚜鏃嬮€熺巼鍒嗙粍鐨勮宸〃銆?

妫€鏌ユā鍨嬫槸鍚﹀湪浠ヤ笅鍖哄煙鏄庢樉澶辨晥锛?

* 浣庣悆閫燂紱
* 鏋佸ぇ鍙戝皠瑙掞紱
* 鏋佺鑷棆锛?
* 澶фí鍚戝亸绉伙紱
* 璁粌鏍锋湰绋€鐤忓尯鍩熴€?

---

# 8. ODE 鍧愭爣绯荤粺

缁熶竴瀹氫箟锛?

* (x)锛氱洰鏍囨柟鍚戯紝鍚戝墠涓烘锛?
* (y)锛氭í鍚戞柟鍚戯紝鍚戝彸涓烘锛?
* (z)锛氱珫鐩存柟鍚戯紝鍚戜笂涓烘銆?

浣嶇疆锛?

[
\boldsymbol r=(x,y,z)
]

閫熷害锛?

[
\boldsymbol v=(v_x,v_y,v_z)
]

---

## 8.1 鍒濋€熷害

璁撅細

* 鐞冮€?(v_0)锛?
* 鍙戝皠浠拌 (\theta)锛?
* 姘村钩鍙戝皠鏂瑰悜 (\phi)銆?

鍒欙細

[
v_x(0)=v_0\cos\theta\cos\phi
]

[
v_y(0)=v_0\cos\theta\sin\phi
]

[
v_z(0)=v_0\sin\theta
]

鍗曚綅鎹㈢畻锛?

[
1\ \mathrm{mph}=0.44704\ \mathrm{m/s}
]

[
1\ \mathrm{rpm}=\frac{2\pi}{60}\ \mathrm{rad/s}
]

[
1\ \mathrm{yd}=0.9144\ \mathrm{m}
]

ODE 鍐呴儴蹇呴』鍏ㄩ儴浣跨敤 SI 鍗曚綅銆?

---

# 9. 鑷棆鍚戦噺鏋勯€?

ODE 鐨勫叕鍏辨帴鍙ｅ繀椤绘帴鏀讹細

```text
spin_rate_rpm
spin_axis_deg
```

棣栧厛楠岃瘉鏁版嵁涓殑鍑犱綍鍏崇郴锛?

[
\omega_{\mathrm{back}}
\approx
\omega\cos\alpha
]

[
\omega_{\mathrm{side}}
\approx
\pm\omega\sin\alpha
]

鍒嗗埆娴嬭瘯姝ｈ礋鍙凤紝浠ユ暟鎹腑瀹為檯 `backspin_rpm`銆乣sidespin_rpm` 鐨勯噸鏋勮宸喅瀹氱鍙风害瀹氥€?

淇濆瓨锛?

```text
q2_spin_geometry_check.csv
```

涓嶅緱鍑粡楠岀洿鎺ュ喅瀹氫晶鏃嬬鍙枫€?

寤虹珛灞€閮ㄥ熀鍚戦噺锛?

[
\boldsymbol e_f=(\cos\phi,\sin\phi,0)
]

[
\boldsymbol e_l=(-\sin\phi,\cos\phi,0)
]

[
\boldsymbol e_z=(0,0,1)
]

浣跨敤鍚庢棆鍜屼晶鏃嬪垎閲忔瀯閫犲叏灞€鑷棆鍚戦噺銆?

蹇呴』纭繚锛?

> 姝ｅ悗鏃嬪湪褰撳墠鍧愭爣瀹氫箟涓嬩骇鐢熷悜涓婄殑椹牸鍔柉鍔涖€?

---

# 10. ODE 妯″瀷灞傜骇

蹇呴』閫愮骇寤虹珛锛岃€屼笉鏄竴娆″畬鎴愬鏉傛ā鍨嬨€?

## ODE-0锛氱湡绌烘姏浣?

鍙€冭檻閲嶅姏锛?

[
\boldsymbol F_g=(0,0,-mg)
]

浣滅敤锛?

* 楠岃瘉鍒濋€熷害鍒嗚В锛?
* 楠岃瘉鍗曚綅鎹㈢畻锛?
* 楠岃瘉钀藉湴浜嬩欢锛?
* 妫€鏌ヨВ鏋愯В涓庢暟鍊艰В涓€鑷存€с€?

---

## ODE-1锛氶噸鍔涳紜绌烘皵闃诲姏

绌烘皵鐩稿閫熷害锛?

[
\boldsymbol u=\boldsymbol v-\boldsymbol v_{\mathrm{wind}}
]

鏃犻鏁版嵁涓嬶細

[
\boldsymbol v_{\mathrm{wind}}=\boldsymbol 0
]

闃诲姏锛?

[
\boldsymbol F_D
===============

-\frac12\rho A C_D
|\boldsymbol u|\boldsymbol u
]

鍏朵腑锛?

[
A=\pi R^2
]

鏍囧畾涓€涓叏灞€ (C_D)銆?

---

## ODE-2锛氶噸鍔涳紜闃诲姏锛嬮┈鏍煎姫鏂姏

鍗囧姏鏂瑰悜瀹氫箟涓猴細

[
\boldsymbol n_L
===============

\frac{\boldsymbol u\times\boldsymbol\omega}
{|\boldsymbol u\times\boldsymbol\omega|}
]

鍗囧姏锛?

[
\boldsymbol F_L
===============

\frac12\rho A C_L
|\boldsymbol u|^2
\boldsymbol n_L
]

棣栧厛寤虹珛棰樼洰瑕佹眰鐨勫父鏁?(C_L) 妯″瀷銆?

---

## ODE-3锛氳嚜鏃嬪洜瀛愭墿灞曟ā鍨?

鐢变簬甯告暟 (C_L) 涓嶈兘鍏呭垎琛ㄨ揪鑷棆閫熺巼澶у皬锛屽彲澧炲姞锛?

[
S=
\frac{R|\boldsymbol\omega|}
{|\boldsymbol u|}
]

[
C_L(S)=k_LS
]

姣旇緝 ODE-2 涓?ODE-3 鐨勬祴璇曢泦璇樊銆?

瑙勫垯锛?

* ODE-2 鐢ㄤ簬鐩存帴鍥炵瓟鈥滈樆鍔涚郴鏁般€佸崌鍔涚郴鏁扳€濓紱
* ODE-3 浣滀负鐗╃悊鏀硅繘妯″瀷锛?
* 鍙湁 ODE-3 鍦ㄦ祴璇曢泦涓婃槑鏄炬洿濂芥椂锛屾墠浣滀负鎺ㄨ崘杞ㄨ抗妯″瀷锛?
* 璁烘枃涓繀椤诲尯鍒嗗父鏁?(C_L) 鍜屽崌鍔涙瘮渚嬪弬鏁?(k_L)銆?

---

# 11. 鏁板€肩Н鍒?

浣跨敤锛?

```python
scipy.integrate.solve_ivp
```

寤鸿锛?

```text
method = RK45 鎴?DOP853
rtol <= 1e-7
atol <= 1e-9
max_step 鍗曠嫭閰嶇疆
```

钀藉湴浜嬩欢锛?

```text
z(t) = 0
direction = -1
terminal = True
```

鍒濆楂樺害浣跨敤棰橀潰缁欏畾鍊硷紱棰橀潰鏈粰鍑烘椂锛屼娇鐢ㄤ竴涓槑纭褰曞湪閰嶇疆涓殑灏忔鍊硷紝闃叉绉垎鍦?(t=0) 绔嬪嵆缁堟銆?

绉垎澶辫触鏃讹細

* 杩斿洖鏄庣‘澶辫触鐘舵€侊紱
* 璁板綍鏍锋湰缂栧彿锛?
* 涓嶅緱杩斿洖绌烘暟缁勫悗缁х画璁＄畻锛?
* 澶辫触鐜囧繀椤昏繘鍏ラ獙璇佹姤鍛娿€?

---

# 12. ODE 杈撳嚭瀹氫箟

杞ㄨ抗缁撴潫鏃讹細

## 椋炶璺濈

[
D_{\mathrm{pred}}
=================

\sqrt{x_{\mathrm{land}}^2+y_{\mathrm{land}}^2}
]

## 妯悜鍋忕Щ

[
Y_{\mathrm{pred}}
=================

y_{\mathrm{land}}
]

## 鏈€楂樼偣楂樺害

[
H_{\mathrm{pred}}
=================

\max_t z(t)
]

## 椋炶鏃堕棿

[
T_{\mathrm{flight}}
===================

t_{\mathrm{land}}
]

闇€瑕佺‘璁ゅ疄娴嬮琛岃窛绂荤殑瀹氫箟鏄惁涓烘按骞虫姘忚窛绂绘垨鐩爣绾挎柟鍚戣窛绂汇€?

鑻ラ闈㈠畾涔変笉鏄庣‘锛?

* 涓荤粨鏋滈噰鐢ㄦ按骞虫姘忚窛绂伙紱
* 鍚屾椂璁＄畻 (x_{\mathrm{land}})锛?
* 姣旇緝鍝瀹氫箟涓庢暟鎹洿涓€鑷达紱
* 灏嗛€夋嫨渚濇嵁鍐欏叆 `approach.md`銆?

---

# 13. ODE 鍙傛暟鏍囧畾

## 13.1 涓ユ牸闃叉娴嬭瘯娉勬紡

鍙娇鐢?70% 璁粌闆嗘爣瀹氾細

```text
C_D
C_L
鎴?k_L
```

30% 娴嬭瘯闆嗕笉鑳藉弬涓庣洰鏍囧嚱鏁般€?

---

## 13.2 鏍囧畾鐩爣

浣跨敤璁粌闆嗙殑椋炶璺濈鍜屾渶楂樼偣锛?

[
J(\theta)
=========

\frac1n
\sum_{i=1}^{n}
\left[
\left(
\frac{\hat D_i-D_i}{s_D}
\right)^2
+
\left(
\frac{\hat H_i-H_i}{s_H}
\right)^2
\right]
]

鍏朵腑锛?

* (\theta=(C_D,C_L)) 鎴?((C_D,k_L))锛?
* (s_D,s_H) 涓鸿缁冮泦鐩爣鏍囧噯宸垨鍏朵粬鏄庣‘灏哄害銆?

妯悜鍋忕Щ鍏堜綔涓哄閮ㄨ瘖鏂紝涓嶈繘鍏ヤ富鏍囧畾鐩爣锛岄槻姝㈡棤椋庛€佹亽瀹氳嚜鏃嬬瓑绠€鍖栧亣璁捐繃搴﹀奖鍝嶄袱涓富鍙傛暟銆?

澧炲姞涓€椤规晱鎰熸€у垎鏋愶細

```text
鍦ㄧ洰鏍囧嚱鏁颁腑鍔犲叆灏忔潈閲嶆í鍚戝亸绉婚」
```

姣旇緝鍙傛暟鍜屾祴璇曡宸槸鍚﹀ぇ骞呭彉鍖栥€?

---

## 13.3 浼樺寲绠楁硶

鐢变簬鍙傛暟缁村害寰堜綆锛屽缓璁細

1. 绮楃綉鏍兼垨宸垎杩涘寲瀵绘壘鍒濆鍖哄煙锛?
2. `least_squares` 鏈夌晫绮剧粏浼樺寲锛?
3. 浣跨敤澶氫釜鍒濆鍊奸噸澶嶏紱
4. 姣旇緝鏄惁鏀舵暃鍒扮浉杩戝弬鏁般€?

鍙傛暟杈圭晫锛?

* 浼樺厛閲囩敤棰橀潰缁欏畾鑼冨洿锛?
* 棰橀潰鏈粰鑼冨洿鏃讹紝浣跨敤鍙В閲婄殑鐗╃悊鑼冨洿锛?
* 鑼冨洿鏉ユ簮蹇呴』鍐欏叆鏂囨。锛?
* 涓嶅緱涓轰簡闄嶄綆璇樊鏃犻檺鏀惧鑼冨洿銆?

---

## 13.4 浠ｈ〃鎬ф牱鏈姞閫?

鑻ュ叏璁粌闆嗙Н鍒嗚繃鎱細

1. 鎸夌悆閫熴€佸彂灏勮銆佽嚜鏃嬮€熺巼鍒嗙锛?
2. 浠庤缁冮泦鎶藉彇绾?150鈥?50 鏉′唬琛ㄦ€ц褰曞仛鍒濆鏍囧畾锛?
3. 鍦ㄥ畬鏁磋缁冮泦涓婄簿璋冩垨楠岃瘉鐩爣鍑芥暟锛?
4. 淇濆瓨浠ｈ〃鏍锋湰缂栧彿銆?

涓嶅緱鍙寫閫夎宸緝灏忕殑璁板綍銆?

---

# 14. 鍙傛暟鍙瘑鍒€ф鏌?

鍙湁涓や釜涓昏鍙傛暟锛屽簲鐢熸垚浜岀淮鐩爣鍑芥暟鏇查潰锛?

```text
q2_ode_parameter_surface.csv
q2_ode_parameter_surface.png
```

妫€鏌ワ細

* 鏄惁瀛樺湪鏄庣‘鍞竴鏋佸皬鍊硷紱
* (C_D) 涓?(C_L) 鏄惁楂樺害琛ュ伩锛?
* 鏈€浼樺€兼槸鍚﹀崱鍦ㄨ竟鐣岋紱
* 鍙傛暟杞诲井鍙樺寲鏄惁瀵艰嚧璇樊澶у箙鍙樺寲銆?

鑻ユ渶浼樺弬鏁颁綅浜庤竟鐣岋紝涓嶈兘鐩存帴瀹ｇО宸茬粡鍑嗙‘浼拌锛屽簲閲嶆柊妫€鏌ワ細

* 鍗曚綅锛?
* 鍗囧姏鏂瑰悜锛?
* 鑷棆绗﹀彿锛?
* 椋炶璺濈瀹氫箟锛?
* 鍙傛暟鑼冨洿锛?
* 妯″瀷缁撴瀯銆?

---

# 15. ODE 娴嬭瘯闆嗚瘎浠?

鍦ㄥ畬鏁?30% 娴嬭瘯闆嗕笂鎶ュ憡锛?

```text
carry RMSE
carry MAPE
apex RMSE
apex MAPE
lateral MAE
flight failure rate
```

妯悜鍋忕Щ鍙兘鎺ヨ繎 0锛屽洜姝わ細

* 涓昏鎶ュ憡缁濆璇樊锛?
* 褰?(|y_{\mathrm{true}}|<5\ \mathrm{yd}) 鏃讹紝涓嶆姤鍛婃櫘閫氱浉瀵硅宸紱
* 鍙澶栨姤鍛婂畨鍏ㄥ綊涓€鍖栬宸紝浣嗗繀椤昏鏄庡畾涔夈€?

鍒嗗埆姣旇緝锛?

```text
ODE-0
ODE-1
ODE-2
ODE-3
```

杩欐牱鎵嶈兘璇佹槑绌烘皵闃诲姏鍜岄┈鏍煎姫鏂姏鍒嗗埆鏀瑰杽浜嗕粈涔堛€?

---

# 16. 鍏稿瀷璁板綍閫夋嫨

鍙粠娴嬭瘯闆嗐€丱DE 蹇呴渶瀛楁瀹屾暣鐨勮褰曚腑閫夋嫨銆?

鐩爣锛?

```text
100 yd
150 yd
200 yd
```

閫夋嫨瑙勫垯锛?

[
i^\ast
======

\arg\min_i
|D_i-D_{\mathrm{target}}|
]

骞跺垪鏃舵寜鏍锋湰缂栧彿閫夋嫨銆?

涓嶅緱鏍规嵁 ODE 璇樊鎸戦€夎〃鐜版渶濂界殑璁板綍銆?

淇濆瓨锛?

```text
q2_typical_records.csv
```

瀛楁锛?

```text
target_distance_yd
sample_id
actual_carry_yd
distance_to_target_yd
ball_speed_mph
launch_angle_deg
launch_direction_deg
spin_rate_rpm
spin_axis_deg
```

---

# 17. 鍏稿瀷璁板綍璇樊琛?

鐢熸垚锛?

```text
q2_ode_typical_errors.csv
```

鑷冲皯鍖呮嫭锛?

```text
sample_id
target_group
model
actual_carry_yd
predicted_carry_yd
carry_absolute_error_yd
carry_relative_error_pct
actual_apex_yd
predicted_apex_yd
apex_absolute_error_yd
apex_relative_error_pct
actual_lateral_yd
predicted_lateral_yd
lateral_absolute_error_yd
flight_time_s
integration_status
```

---

# 18. 杞ㄨ抗鍥?

蹇呴』鐢熸垚锛?

## 涓夌淮杞ㄨ抗鍥?

```text
q2_typical_trajectories_3d.png
```

灞曠ず绾?100銆?50銆?00 yd 涓夋潯杞ㄨ抗銆?

## 渚ц鍥?

```text
q2_typical_trajectories_side.png
```

灞曠ず锛?

```text
x-z
```

渚夸簬瑙傚療鏈€楂樼偣銆?

## 淇鍥?

```text
q2_typical_trajectories_top.png
```

灞曠ず锛?

```text
x-y
```

渚夸簬瑙傚療妯悜寮洸銆?

鎵€鏈夎建杩圭偣淇濆瓨鑷筹細

```text
q2_typical_trajectories.csv
```

瀛楁锛?

```text
sample_id
target_group
model
time_s
x_m
y_m
z_m
x_yd
y_yd
z_yd
```

---

# 19. 鐏垫晱搴﹀垎鏋?

## 19.1 鐩戠潱妯″瀷

涓?70%/30% 鍒掑垎淇濇寔涓嶅彉锛屽悓鏃惰繘琛岋細

```text
30 涓笉鍚岄殢鏈虹瀛愮殑閲嶅 70%/30% 鍒掑垎
```

浠呯敤浜庣ǔ瀹氭€у垎鏋愶紝涓嶆浛浠ｉ鐩姹傜殑涓诲垝鍒嗐€?

鎶ュ憡锛?

```text
RMSE mean/std
MAPE mean/std
妯″瀷鑳滃嚭棰戠巼
```

---

## 19.2 ODE 鍙傛暟

鎸夌収閰嶇疆瀵瑰弬鏁拌繘琛岋細

```text
-20%
-10%
+10%
+20%
```

鎵板姩銆?

鎶ュ憡瀵逛互涓嬭緭鍑虹殑褰卞搷锛?

```text
椋炶璺濈
鏈€楂樼偣楂樺害
妯悜鍋忕Щ
椋炶鏃堕棿
```

---

## 19.3 鏁板€肩Н鍒?

姣旇緝锛?

```text
涓嶅悓 rtol
涓嶅悓 atol
涓嶅悓 max_step
RK45 涓?DOP853
```

鑻ヨ緭鍑哄樊寮傚凡缁忚繙灏忎簬妯″瀷璇樊锛屽垯涓嶉渶瑕佺户缁彁楂樼Н鍒嗙簿搴︺€?

---

## 19.4 妯″瀷鍋囪

鑷冲皯姣旇緝锛?

```text
鏃犻 vs 灏忓箙鍋囪椋庨€?
鎭掑畾鑷棆 vs 绠€鍗曟寚鏁拌“鍑?
甯告暟 CL vs 鑷棆鍥犲瓙 CL
```

杩欎簺浣滀负妯″瀷灞€闄愭€у垎鏋愶紝涓嶄竴瀹氬叏閮ㄨ繘鍏ユ渶缁堜富妯″瀷銆?

---

# 20. 鎺ㄨ崘浠ｇ爜缁撴瀯

```text
questions/q2/scripts/
鈹溾攢鈹€ pipeline.py
鈹溾攢鈹€ preprocessing.py
鈹溾攢鈹€ supervised.py
鈹溾攢鈹€ ode_model.py
鈹溾攢鈹€ calibrate_ode.py
鈹溾攢鈹€ validate.py
鈹斺攢鈹€ visualize.py
```

## `preprocessing.py`

璐熻矗锛?

* 鍔犺浇 q1 娓呮礂鏁版嵁锛?
* 瀛楁楠岃瘉锛?
* 璁粌娴嬭瘯鍒掑垎锛?
* 鍗曚綅鎹㈢畻锛?
* 鑷棆鍑犱綍妫€鏌ワ紱
* 鍏稿瀷璁板綍閫夋嫨銆?

## `supervised.py`

璐熻矗锛?

* 鍩虹嚎妯″瀷锛?
* 闈炵嚎鎬фā鍨嬶紱
* 璁粌闆嗗唴閮ㄤ氦鍙夐獙璇侊紱
* 娴嬭瘯棰勬祴锛?
* Bootstrap 缃俊鍖洪棿锛?
* 妯″瀷淇濆瓨銆?

## `ode_model.py`

璐熻矗锛?

* 鍧愭爣鍜屽垵濮嬬姸鎬侊紱
* 閲嶅姏銆侀樆鍔涖€佸崌鍔涳紱
* 钀藉湴浜嬩欢锛?
* 鏁板€肩Н鍒嗭紱
* 杞ㄨ抗杈撳嚭锛?
* 鍗曟潯璁板綍妯℃嫙銆?

璇ユā鍧楀繀椤昏兘琚涓夐棶鐩存帴瀵煎叆銆?

## `calibrate_ode.py`

璐熻矗锛?

* 鍙傛暟鐩爣鍑芥暟锛?
* 鍙傛暟杈圭晫锛?
* 澶氬垵濮嬪€间紭鍖栵紱
* 浠ｈ〃鏍锋湰鎶藉彇锛?
* 鍙傛暟鏇查潰锛?
* 璁粌鏍囧畾涓庢祴璇曡瘎浠枫€?

## `validate.py`

璐熻矗锛?

* 鏁版嵁娉勬紡妫€鏌ワ紱
* 娴嬭瘯闆嗗喕缁撴鏌ワ紱
* 鏁板€煎崟浣嶆鏌ワ紱
* 鐪熺┖瑙ｆ瀽瑙ｅ鐓э紱
* 鍙傛暟杈圭晫妫€鏌ワ紱
* 绉垎澶辫触妫€鏌ワ紱
* 缁撴灉琛ㄤ竴鑷存€э紱
* 鐏垫晱搴﹀垎鏋愩€?

## `visualize.py`

璐熻矗鎵€鏈夊浘琛ㄥ強鐢熷浘鏁版嵁銆?

---

# 21. 閰嶇疆鏂囦欢

鍦?`configs/default.yaml` 涓鍔狅細

```yaml
q2:
  input_path: data/processed/golf_shots_clean.csv
  output_dir: questions/q2/artifacts
  random_seed: 2026

  split:
    test_size: 0.30

  features:
    launch_state:
      - ball_speed_mph
      - launch_angle_deg
      - launch_direction_deg
      - spin_rate_rpm
      - spin_axis_deg

    full_shot:
      - ball_speed_mph
      - launch_angle_deg
      - launch_direction_deg
      - spin_rate_rpm
      - spin_axis_deg
      - club_speed_mph
      - attack_angle_deg

  targets:
    - carry_distance_yd
    - apex_height_yd

  cross_validation:
    folds: 5

  repeated_split:
    runs: 30

  bootstrap:
    iterations: 1000
    confidence_level: 0.95

  supervised:
    models:
      - dummy
      - linear
      - ridge
      - extra_trees
      - hist_gradient_boosting

  physics:
    mass_kg: null
    radius_m: null
    air_density_kg_m3: null
    gravity_m_s2: null
    initial_height_m: null
    source: "浠庨闈㈠～鍐欙紝涓嶅緱鐚滄祴"

  ode:
    model_variants:
      - vacuum
      - drag
      - constant_lift
      - spin_factor_lift

    solver:
      method: DOP853
      rtol: 1.0e-7
      atol: 1.0e-9
      max_step: 0.02

    parameter_bounds:
      cd: null
      cl: null
      lift_scale: null

    sensitivity_relative_changes:
      - -0.20
      - -0.10
      - 0.10
      - 0.20

  plotting:
    dpi: 300
```

鎵€鏈?`null` 椤瑰湪璇诲彇棰橀潰鎴栫‘璁ゆ潵婧愬悗濉啓銆?

---

# 22. 杈撳嚭鏂囦欢

## 鐩戠潱棰勬祴

```text
q2_data_split.csv
q2_supervised_cv_results.csv
q2_supervised_metrics.csv
q2_supervised_predictions.csv
q2_supervised_bootstrap_ci.csv
q2_supervised_error_groups.csv
```

## ODE

```text
q2_spin_geometry_check.csv
q2_ode_parameters.csv
q2_ode_model_comparison.csv
q2_ode_test_predictions.csv
q2_ode_test_metrics.csv
q2_ode_failures.csv
q2_ode_parameter_surface.csv
q2_ode_sensitivity.csv
```

## 鍏稿瀷璁板綍

```text
q2_typical_records.csv
q2_ode_typical_errors.csv
q2_typical_trajectories.csv
```

## 鍥?

```text
q2_prediction_scatter_carry.png
q2_prediction_scatter_apex.png
q2_residuals_carry.png
q2_residuals_apex.png
q2_ode_parameter_surface.png
q2_typical_trajectories_3d.png
q2_typical_trajectories_side.png
q2_typical_trajectories_top.png
q2_ode_model_comparison.png
q2_ode_sensitivity.png
```

## 妯″瀷涓庡厓鏁版嵁

```text
questions/q2/artifacts/models/
q2_carry_model.joblib
q2_apex_model.joblib
q2_ode_parameters.json
run_metadata.json
```

---

# 23. 蹇呴』瀹炵幇鐨勯獙璇?

## 鏁版嵁鍒掑垎

* 璁粌闆嗙害鍗?70%锛?
* 娴嬭瘯闆嗙害鍗?30%锛?
* 鏍锋湰缂栧彿鏃犻噸鍙狅紱
* 鎵€鏈夋ā鍨嬩娇鐢ㄧ浉鍚屼富娴嬭瘯闆嗭紱
* 娴嬭瘯闆嗙紪鍙蜂繚瀛樺悗涓嶅緱鍙樺寲銆?

## 鐩戠潱妯″瀷

* 鎻掕ˉ鍙湪璁粌娴佹按绾垮唴閮ㄦ嫙鍚堬紱
* 鏍囧噯鍖栧彧鍦ㄨ缁冩祦姘寸嚎鍐呴儴鎷熷悎锛?
* 娴嬭瘯闆嗕笉鍙備笌瓒呭弬鏁伴€夋嫨锛?
* 鎸囨爣鍧囩敱淇濆瓨鐨勬祴璇曢娴嬮噸鏂拌绠楋紱
* 棰勬祴琛ㄨ鏁扮瓑浜庢祴璇曢泦鏍锋湰鏁帮紱
* Dummy 妯″瀷蹇呴』瀛樺湪銆?

## ODE

* mph銆乺pm銆亂d 杞崲鍗曞厓娴嬭瘯閫氳繃锛?
* 鐪熺┖鏁板€艰В涓庤В鏋愯В璇樊浣庝簬瀹瑰樊锛?
* 姝ｅ悗鏃嬭兘澶熶骇鐢熷悜涓婂崌鍔涳紱
* 鏃犱晶鏃嬩笖鍙戝皠鏂瑰悜涓?0 鏃讹紝鐞嗚涓婃í鍚戜綅绉绘帴杩?0锛?
* 钀藉湴浜嬩欢鍙戠敓鍦ㄤ笅闄嶉樁娈碉紱
* 杞ㄨ抗涓笉瀛樺湪鏄庢樉 NaN 鎴?Inf锛?
* 鏈€浼樺弬鏁颁笉搴旀棤瑙ｉ噴鍦板仠鍦ㄨ竟鐣岋紱
* 绉垎澶辫触鐜囧繀椤昏緭鍑恒€?

## 鏂囨。

* `results.md` 涓殑姣忎釜鎸囨爣閮借兘鍦?CSV 涓壘鍒帮紱
* 鍏稿瀷璁板綍缂栧彿涓庨€夋嫨琛ㄤ竴鑷达紱
* 鍥惧拰鐢熷浘鏁版嵁鎴愬瀛樺湪锛?
* 鐗╃悊甯告暟鍏锋湁鏉ユ簮锛?
* 娴嬭瘯闆嗘病鏈夎鐢ㄤ簬璋冨弬銆?

楠岃瘉澶辫触鏃剁▼搴忚繑鍥為潪闆堕€€鍑虹爜銆?

---

# 24. 璁烘枃缁撴灉缁撴瀯

鏇存柊 `questions/q2/results.md` 鏃朵娇鐢細

```text
1. 鏁版嵁鍒掑垎涓庡彉閲忛€夋嫨
2. 鐩戠潱棰勬祴鍩虹嚎
3. 鐩戠潱涓绘ā鍨嬪強娴嬭瘯缁撴灉
4. 棰勬祴璇樊璇婃柇
5. 涓夌淮鍔ㄥ姏瀛︽柟绋?
6. 闃诲姏鍜屽崌鍔涘弬鏁版爣瀹?
7. ODE 妯″瀷閫愮骇姣旇緝
8. 娴嬭瘯闆?ODE 璇樊
9. 鍏稿瀷 100/150/200 yd 杞ㄨ抗
10. 鐏垫晱搴︿笌鍙傛暟鍙瘑鍒€?
11. 鐩戠潱妯″瀷涓?ODE 鐨勫姛鑳藉樊寮?
12. 妯″瀷灞€闄愭€?
```

鏈€缁堢粨璁哄簲鏄庣‘鍖哄垎锛?

* 鐩戠潱妯″瀷棰勬祴绮惧害鏇撮珮锛?
* ODE 妯″瀷鍏锋湁杞ㄨ抗鐢熸垚鍜岀墿鐞嗚В閲婅兘鍔涳紱
* ODE 璇樊鍙兘鏉ヨ嚜鎭掑畾绌烘皵鍔ㄥ姏鍙傛暟銆佹棤椋庡亣璁俱€佽嚜鏃嬭“鍑忕己澶卞拰娴嬮噺璇樊锛?
* 绗笁闂簲浼樺厛澶嶇敤缁忚繃楠岃瘉鐨?ODE 鎺ュ彛鍜屽彂灏勭姸鎬佷唬鐞嗘ā鍨嬨€?

---

# 25. 鎺ㄨ崘鎻愪氦椤哄簭

```text
docs(q2): finalize supervised and ODE modeling plan
```

```text
feat(q2): add fixed split and supervised baselines
```

```text
feat(q2): implement supervised model selection and diagnostics
```

```text
feat(q2): implement 3d golf ball ODE solver
```

```text
feat(q2): calibrate drag and lift parameters
```

```text
feat(q2): add typical trajectory analysis
```

```text
feat(q2): add validation and sensitivity analysis
```

```text
docs(q2): publish reproducible results
```

---

# 26. 绗竴闃舵鍋滄鐐?

鏈疆鍏堝畬鎴愪互涓嬪唴瀹癸紝涓嶈涓€娆℃€х洿鎺ュ仛鍒版渶缁堣鏂囷細

1. 淇 q2 閰嶇疆鍜?manifest锛?
2. 鍥哄畾骞朵繚瀛?70%/30% 鏁版嵁鍒掑垎锛?
3. 瀹屾垚 Dummy銆佺嚎鎬с€佸箔鍥炲綊銆丒xtraTrees銆丠istGradientBoosting锛?
4. 杈撳嚭鐩戠潱妯″瀷娴嬭瘯鎸囨爣锛?
5. 瀹屾垚鐪熺┖鎶涗綋鍜屼粎闃诲姏 ODE锛?
6. 瀹屾垚鍗曚綅鎹㈢畻鍙婅В鏋愯В楠岃瘉锛?
7. 鏆備笉瀹ｇО宸茬粡寰楀埌鏈€缁?(C_D,C_L)銆?

瀹屾垚鍚庤繑鍥烇細

```text
1. 淇敼鏂囦欢鍒楄〃
2. 鍥哄畾娴嬭瘯闆嗘牱鏈暟
3. 涓や釜鐩爣鐨勬ā鍨嬫寚鏍?
4. 鏈€浼樼洃鐫ｆā鍨?
5. 鐪熺┖鍜岄樆鍔?ODE 楠岃瘉缁撴灉
6. 鐗╃悊甯告暟鍙婃潵婧?
7. 灏氭湭瀹屾垚鐨勬爣瀹氬唴瀹?
8. Git commit
```

纭鍩虹灞傛纭悗锛屽啀杩涘叆鍗囧姏妯″瀷涓庡弬鏁版爣瀹氥€?
