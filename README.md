# DeFCoN ChainLock és PoSe skálaszimulátor

Ez a repository futtatható, Core-native C++ tesztharnesst tartalmaz. A
`core/src/test/llmq_scale_simulator_tests.cpp` közvetlenül a DeFCoN Core production
`CDeterministicMNList::CalculateQuorum()` függvényét hívja, tehát a quorum selection
algoritmust nem implementálja újra.

## Gyors indítás

Előfeltételek:

- DeFCoN Core `v22.1.x` forrás;
- a Core szokásos build- és tesztfüggőségei;
- Bash és Python 3 az integrációs scripthez.

WSL alatt:

```bash
git clone https://github.com/minuszka/defcon-chainlock-pose-scalability-testplan.git
cd defcon-chainlock-pose-scalability-testplan

# Tesztforrás integrálása a Core forrásba:
./scripts/install-into-core.sh /home/stejn/DEFCON

# A Core meglévő buildfolyamatával fordítsd újra a test_defcon targetet.
cd /home/stejn/DEFCON
make -C src test/test_defcon

# Gyors futás:
cd /path/to/defcon-chainlock-pose-scalability-testplan
./scripts/run-simulator.sh /home/stejn/DEFCON quick
```

A teljes, 150–15 000 MN-es mátrix:

```bash
./scripts/run-simulator.sh /home/stejn/DEFCON full
```

Out-of-tree buildnél a build gyökerét add meg:

```bash
./scripts/run-simulator.sh /home/stejn/DEFCON/build quick
```

## Mit futtat a program?

- valódi `CDeterministicMNList` objektumokat készít;
- a Core saját `CalculateQuorum()` kódjával választ Q25 és Q60 quorumokat;
- 5–30% független kiesést;
- koncentrált provider- és ASN-kiesést;
- 25/33/40% operator-koncentrációt;
- 10/25/40/50% mixed-version populációt;
- flappelő node-okat;
- késleltetett DKG-üzeneteket modellez;
- méri a DKG minimum és signing threshold teljesülését;
- méri az egymást követő quorumok átfedését és selection-eloszlását;
- CSV és JSONL eredményt készít.
- a futás végén automatikusan ellenőrzi a két formátum sorszámát, JSON
  érvényességét, kötelező szcenárióit és számláló-invariánsait.

Quick mód:

```text
populációk: 150,300,500
roundok:    100
seed:       12648430
```

Full mód:

```text
populációk: 150,300,500,1500,5000,10000,15000
roundok:    10000
```

Eredmények:

```text
results/quick/results.csv
results/quick/results.jsonl
```

Az első implementáció a valódi Core quorum selectiont használja, a DKG hálózati
fázisait pedig determinisztikus fault modellel értékeli. Valódi BLS/DKG
message-state-machine és Docker/netem végrehajtás a következő implementációs réteg.

## Biztonsági hatókör

A telepítő kizárólag:

- `src/test/llmq_scale_simulator_tests.cpp`;
- `src/Makefile.test.include`

tesztterületeket érinti. Consensus-paramétert, mainnet-konfigurációt vagy production
ChainLock kódot nem módosít.

Eltávolítás:

```bash
./scripts/uninstall-from-core.sh /home/stejn/DEFCON
```

---

# Részletes audit- és tesztterv

## 0. Hatókör és reprodukálhatóság

Ez a dokumentum statikus kódaudit és megvalósítható tesztterv. Consensus-paramétert, mainnet-konfigurációt és a Core forrását nem módosítottam.

- Vizsgált repository: `/home/stejn/DEFCON`
- Vizsgált ág/ref: `v22.1.x`
- Vizsgált commit: `fd75a6915209685434e0d4ab4cbd1ec4fad6fd10`
- A munkakönyvtár ténylegesen a `feature/gui-multisig-wallet` ágon állt, két meglévő módosítással (`src/chainparamsseeds.h`, `src/net.cpp`). Ezeket érintetlenül hagytam; az audit a `v22.1.x` commit exportján készült.
- A bemeneti kérés a „shadow mode” felsorolás közepén, a „méri a DKG-t és al” szövegnél megszakad. Az addig megadott követelményeket teljesnek tekintettem.

## 1. Vezetői összefoglaló

### 1.1. Legfontosabb megállapítások

1. A mainnet ChainLock típusa jelenleg `LLMQ_400_60`, de a DeFCoN paraméterei valójában `size=400`, `minSize=4`, `threshold=3`. A név és a komment így félrevezető: ez nem 240-of-400, hanem 3 share-ből helyreállítható aláírás, és már 4 valid taggal létrejöhet commitment.
2. Ugyanebben a táblában az `LLMQ_50_60` és `LLMQ_60_75` is `minSize=3`, `threshold=3`. Ezek mainneten regisztrálva vannak, de az `IsQuorumTypeEnabledInternal()` mainneten letiltja őket.
3. A ChainLock típus minden magasságra egyetlen globális mezőből, a `consensus.llmqTypeChainLocks` értékéből jön. A historical CLSIG ellenőrzés nem signed-height profil-resolverrel működik.
4. A `CChainLockSig` wire-formátuma nem tartalmaz LLMQ típust vagy profilverziót; csak `(height, blockHash, signature)` mezőket.
5. A recovered-signature konfliktusnál az első `(llmqType,id)` rekord marad az adatbázisban. A második, eltérő valid recovered signature csak logbejegyzést eredményez, majd eldobódik. Tartós, mindkét aláírást megőrző evidence nincs.
6. A ChainLock handler ugyanazon vagy alacsonyabb magasságú CLSIG-et még ellenőrzés előtt eldob, ha már van `bestChainLock`. Így ugyanazon magasság két valid CLSIG-je nem lesz külön bizonyítékként megőrizve.
7. A `bestChainLock` maga memóriában él. Restart után a node a hálózattól vagy coinbase-adattól építi újra a releváns állapotot; nincs dedikált, tartós ChainLock-conflict journal.
8. PoSe közvetlenül függ a mined final commitment `validMembers` bitjeitől. Egy kimaradó tag az adott DKG után a dinamikus maximum 66%-ának megfelelő büntetést kap. Két közeli DKG-kiesés tipikusan bant okoz; blokkonként csak 1 pont gyógyul.
9. A 60/44/41 profil lényegesen jobb safety-t ad, mint a 25/22/17, de elfogadása csak mérés után indokolt. A minimum két 41-es aláíróhalmaz metszete 60 tagban 22; a minimum két 17-es halmaz metszete 25 tagban 9. Ez nem teszi „matematikailag lehetetlenné” a double lockot: a metszetben levő hibás/rosszindulatú tagok dupla aláírása továbbra is döntő.
10. Automatikus, élő MN-szám alapú profilváltást nem szabad bevezetni. A resolver kizárólag előre rögzített, height-aktivált, egyirányú profilt választhat, a CLSIG `signed height` értéke alapján.

### 1.2. Azonnali döntési javaslat

- A Q60 redesign külön consensus release legyen.
- A jelenlegi 3-share ChainLock konfigurációt release-blocking kockázatként kell kezelni, de ebben a körben ne módosítsuk.
- Először készüljön determinisztikus szimulátor, conflict-evidence teszt és shadow telemetry.
- A Q60 mainnet-aktiváció csak akkor kapjon go döntést, ha a DKG/liveness, koncentrációs safety, mixed-version, restart/reindex és partíciós kapuk mind teljesülnek.

## 2. Tényleges implementáció

### 2.1. Paraméterek és mainneten elérhető típusok

A típusok és paraméterek helye:

- `src/llmq/params.h`: `Consensus::LLMQType`, `LLMQParams`, `available_llmqs`
- `src/chainparams.cpp`: `CChainParams::AddLLMQ()`, mainnet konstruktor
- `src/llmq/options.cpp`: `IsQuorumTypeEnabledInternal()`

Mainneten a `chainparams.cpp` ezeket regisztrálja:

| Típus | Paraméter a vizsgált kódban | Mainnet enabled? | Szerep |
|---|---:|---:|---|
| `LLMQ_50_60` | 50 / 3 / 3 | nem | regisztrálva, de options tiltja |
| `LLMQ_60_75` | 60 / 3 / 3 | nem | DIP0024 IS mező erre mutat, de options mainneten tiltja |
| `LLMQ_400_60` | 400 / 4 / 3 | igen | ChainLocks |
| `LLMQ_400_85` | 400 / 350 / 340 | igen | MNHF |
| `LLMQ_100_67` | 100 / 80 / 67 | DIP0020 után | Platform |
| `LLMQ_25_67` | 25 / 22 / 17 | nem is regisztrált mainnetre | testnet |

A táblázatban a három szám: `size / minSize / threshold`.

Fontos különbség:

- „Regisztrált” azt jelenti, hogy `Params().GetLLMQ(type)` megtalálja.
- „Enabled” azt jelenti, hogy az adott magasságon az `IsQuorumTypeEnabled()` engedi.
- ChainLockhoz ténylegesen használt azt jelenti, hogy a `consensus.llmqTypeChainLocks` erre mutat. Ez jelenleg kizárólag `LLMQ_400_60`.

### 2.2. Quorumtagok determinisztikus kiválasztása

Fő útvonal:

1. `llmq::utils::GetAllQuorumMembers()` – `src/llmq/utils.cpp`
2. nem rotált típusnál `ComputeQuorumMembers()`
3. az adott base/work blockhoz tartozó `CDeterministicMNList`
4. `CDeterministicMNList::CalculateQuorum()` – `src/evo/deterministicmns.cpp`
5. score: SHA256 a `confirmedHashWithProRegTxHash` és a quorum modifier felett
6. csökkenő score-rendezés, az első `min(size, eligible_count)` tag kiválasztása

A kiválasztás nem hálózati mintavétel; az azonos chain state-et látó node-ok determinisztikusan ugyanazt kapják. Forkon azonban eltérhet a work/base block, a modifier és akár a deterministic MN list is.

### 2.3. DKG és final commitment

Érintett fő komponensek:

- `src/llmq/dkgsession.cpp`: DKG fázisok, valid member állapot, premature/final commitment
- `src/llmq/dkgsessionmgr.cpp`: sessionök és verified contribution adatok
- `src/llmq/commitment.cpp`: `CFinalCommitment::Verify()`
- `src/llmq/blockprocessor.cpp`: commitment blockba fogadása
- `src/llmq/quorums.cpp`: aktív quorumok beolvasása és signing quorum kiválasztása

A `CFinalCommitment::Verify()` külön ellenőrzi:

- bitset méretek;
- `CountValidMembers() >= minSize`;
- `CountSigners() >= minSize`;
- quorum public key és vvec hash;
- member aggregate signature;
- recovered quorum signature.

Ezért a túl alacsony `minSize` és `threshold` nem pusztán policy: közvetlenül meghatározza, milyen gyenge commitment és recovered signature consensus-valid.

### 2.4. ChainLock quorum kiválasztása és ellenőrzése

Signing:

- `CChainLocksHandler::TrySignChainTip()` létrehozza a request ID-t: `SerializeHash("clsig", height)`.
- `CSigningManager::AsyncSignIfMember(consensus.llmqTypeChainLocks, ...)` választ signing quorumot.
- `SelectQuorumForSigning()` a signed height körüli aktív quorum poolból determinisztikusan választ az ID alapján.

Ellenőrzés:

- `CChainLocksHandler::VerifyChainLock()` újra a jelenlegi globális `consensus.llmqTypeChainLocks` típust veszi.
- `llmq::VerifyRecoveredSig()` a `signedAtHeight` alapján megtalálja az akkori aktív quorumot, de csak a hívó által átadott egyetlen LLMQ típuson belül.
- A sign hash tartalmazza az LLMQ típust és a választott quorum hashét.

Következmény: a quorum példány történelmileg helyesen, signed height alapján választódik, de a quorum **profil/típus nem**. Ha helyben átírnánk a meglévő `LLMQ_400_60` paramétereit vagy globálisan más típusra állítanánk a ChainLock mezőt, régi CLSIG-ek ellenőrzése sérülne.

### 2.5. Konfliktusos recovered signature és CLSIG

Recovered signature:

- `CSigningManager::ProcessRecoveredSig()` – `src/llmq/signing.cpp`
- DB kulcs: `("rs_r", llmqType, id)`
- ha ugyanerre az ID-re már van recovered signature és a sign hash más:
  - log: `conflicting recoveredSig`;
  - az új rekord nem íródik ki;
  - listener nem kapja meg;
  - peer relay nincs;
  - tartós conflict evidence nincs.

Lokális double-vote védelem:

- `AsyncSignIfMember()` a `("rs_v", llmqType, id)` vote rekord alapján normál esetben nem ír alá másik `msgHash`-t;
- ez a rekord LevelDB-ben tartós, de kor alapú cleanup eltávolítja;
- a védelem egy lokális node-ra és egy `(type,id)` kulcsra vonatkozik.

CLSIG:

- `CChainLocksHandler::ProcessNewChainLock()` először a `seenChainLocks` memóriamapba teszi a hash-t;
- ha `height <= bestChainLock.height`, azonnal visszatér, ellenőrzés nélkül;
- csak magasabb, valid CLSIG válhat bestté;
- ugyanazon height konfliktus nem lesz külön kezelve vagy perzisztálva;
- `seenChainLocks` 24 óra után ürül és restartot nem él túl.

Ez magyarázza, miért fontos a megfigyelt log: a kód szerint valódi, már kriptográfiailag előellenőrzött recovered-signature konfliktus jutott el a `ProcessRecoveredSig()` pontig. A log önmagában nem bizonyítja az okot; lehet forkelt quorum state, eltérő chain/quorum selection, kulcs-/state-recovery hiba vagy tényleges dupla share. Viszont a jelenlegi evidenciakezelés kevés az utólagos eldöntéshez.

### 2.6. PoSe és DKG-kiesés

Fő útvonal:

- `CDeterministicMNManager::HandleQuorumCommitment()` – `src/evo/deterministicmns.cpp`
- minden kiválasztott, de `qc.validMembers[i] == false` tagnál:
  - `PoSePunish(..., CalcPenalty(66))`
- `CalcMaxPoSePenalty() = max(100, registered_MN_count)`
- minden feldolgozott blokknál a nem bannolt node-ok büntetése 1 ponttal csökken
- max elérésekor PoSe ban; a bannolt node nem gyógyul automatikusan, ProUpServTx-alapú revival kell

Példa:

- 15 000 regisztrált MN esetén egy DKG-kiesés kb. 9 900 pont;
- 150 MN esetén kb. 99 pont;
- két közeli DKG-kiesés a komment szerinti szándék alapján bant okozhat;
- a gyógyulási idő és a DKG intervallum aránya ezért skálával változik.

Ez nagyon erős, közvetlen DKG→PoSe csatolás. Provider/ASN kiesés egyszerre sok quorumtagot tehet invaliddá, majd consensus-state-ben büntetheti őket és kizárhatja őket a reward eligibilityből. Ezt nem elegendő csak DKG completion rate-tel mérni.

## 3. Profilok objektív összevetése

| Profil | `n/min/t` | Minimum két threshold-halmaz metszete `2t-n` | DKG invalid tolerancia `n-min` | Signing kieséstűrés `n-t` |
|---|---:|---:|---:|---:|
| jelenlegi ChainLock | 400/4/3 | nincs klasszikus pozitív threshold-metszet | 396 | 397 |
| Q25 jelölt | 25/22/17 | 9 | 3 | 8 |
| Q60 jelölt | 60/44/41 | 22 | 16 | 19 |

Megjegyzések:

- A jelenlegi 3-of-400 konfiguráció safety szempontból nem kezelhető „400-as quorumként”; három kompromittált aktív share elegendő lehet.
- Q25 esetén két 17-es halmaz legalább 9 tagban metszi egymást. Kilenc dupla aláíró elég lehet két thresholdhoz.
- Q60 esetén a minimum metszet 22. Ez erősebb abszolút safety margin, de 22 hibás/rosszindulatú metszeti tag mellett továbbra sem „double lock impossible”.
- Q60 livenesshez 41 online, együttműködő valid tag kell. A DKG commitmenthez legalább 44 valid tag kell, ami 16 kiesőt enged.
- A `minSize=44`, `threshold=41` közt csak 3 tag headroom van a DKG utáni kiesésre, ha éppen minimum-valid commitment jön létre. Emiatt külön mérendő a `validMembers` eloszlás alsó farka, nem csak az átlag.

Előzetes álláspont: a 60/44/41 jó jelölt, de nem tekinthető kész döntésnek. A 25/22/17 kis hálózaton jobb liveness-t adhat, de gyengébb a metszeti safety és lényegesen érzékenyebb a DKG minimumra. Élő MN-szám alapján automatikus váltás egyikre sem elfogadható.

## 4. V2 finality architektúra – implementációs terv, kódolás nélkül

### 4.1. Consensus-modell

1. Vegyünk fel új, soha korábban nem használt LLMQ típust, például `LLMQ_60_68_CL_V2`.
2. Paraméterei külön rekordban legyenek; a régi `LLMQ_400_60` rekordot ne írjuk át.
3. Legyen fix `CL_V2_ACTIVATION_HEIGHT`, vagy megfelelő deployment lezárása után consensusban rögzített aktivációs magasság.
4. Egyetlen resolver:

   `GetChainLockLLMQTypeForSignedHeight(consensus, signed_height)`

   - `< activation`: legacy típus;
   - `>= activation`: V2 típus;
   - csak height és statikus consensus paraméter alapján dönt;
   - nem néz live MN countot, peer állapotot, sporkot vagy lokális konfigurációt.
5. Signing és verification ugyanazt a resolvert használja.
6. Reorg/fork esetén a signed heighthez rendelt profil nem változhat.
7. Több jövőbeli tier esetén rendezett, egyirányú `(activation_height, llmq_type)` schedule legyen, és tiltsuk a visszaváltást.

### 4.2. Wire- és DB-kompatibilitás

A régi `CChainLockSig` típusmező nélkül is feloldható signed height alapján. Ez a legkisebb wire-változás, de:

- domain separationt az új LLMQ type már biztosít a sign hashben;
- az RPC-knek vissza kell adniuk a resolved típust és profilverziót;
- conflict evidence kulcs tartalmazza a resolved típust, heightet, request ID-t, block hash-t, quorum hash-t és a teljes signature-t;
- régi és új típus recovered-signature DB rekordja ne ütközzön.

Ha CLSIG v2 wire-verzió készül, legyen explicit verzió/type mező, de a verifier akkor is ellenőrizze, hogy az deklarált típus megfelel-e a signed-height resolvernek. A peer által közölt típus nem lehet szabad választás.

### 4.3. Conflict evidence

Új, append-only vagy duplikációbiztos tárolás szükséges:

- mindkét valid recovered signature/CLSIG megőrzése;
- first-seen timestamp, peer ID csak diagnosztikai metaadatként;
- resolved quorum type/hash és sign hash;
- validáció státusza és hiba oka;
- restart/reindex után visszaolvasható;
- RPC: `getchainlockconflicts`, exportálható JSON;
- metrika és egyszeri magas prioritású log;
- evidence fogadása önmagában ne válasszon „nyertest” és ne változtasson chain state-et.

### 4.4. Várhatóan érintett fájlok és függvények

| Terület | Fájl / függvény |
|---|---|
| új típus és paraméter | `src/llmq/params.h` |
| mainnet regisztráció, activation height | `src/chainparams.cpp`, `src/consensus/params.h` |
| type enable szabály | `src/llmq/options.cpp/.h` |
| profil resolver | új kis consensus helper vagy `src/llmq/chainlocks.*` |
| signing | `CChainLocksHandler::TrySignChainTip()`, `CSigningManager::AsyncSignIfMember()` |
| historical verification | `CChainLocksHandler::VerifyChainLock()`, coinbase best-CL ellenőrzési útvonal, `llmq::VerifyRecoveredSig()` hívói |
| CLSIG formátum, ha verziózott | `src/llmq/clsig.h/.cpp`, P2P/RPC serializer |
| recovered-sig konfliktus | `src/llmq/signing.cpp/.h`, `CRecoveredSigsDb`, `ProcessRecoveredSig()` |
| quorum/DKG | `src/llmq/commitment.cpp`, `blockprocessor.cpp`, `dkgsession*.cpp`, `quorums.cpp`, `utils.cpp` |
| PoSe | `CDeterministicMNManager::HandleQuorumCommitment()`, PoSe metrikák |
| RPC/telemetria | `src/rpc/quorums.cpp`, új finality diagnostics RPC |
| tesztek | `src/test/*`, `test/functional/feature_llmq_chainlocks.py`, új profile/conflict/reindex tesztek |
| build | `src/Makefile.test.include` vagy a projekt aktuális CMake targetjei |

## 5. A réteg – determinisztikus skála-szimulátor

### 5.1. Megvalósítás

Javasolt egy Core-native C++ test executable vagy Boost test target:

- `src/test/llmq_scale_simulator_tests.cpp`
- opcionális CLI driver: `src/test/llmq_scale_simulator.cpp`
- közös fixture: `src/test/util/llmq_simulation.*`

Nem szabad újraimplementálni a kiválasztást. A harness:

1. valódi `CDeterministicMN`, `CDeterministicMNState`, `CDeterministicMNList` objektumokat gyárt fix seedből;
2. valós `confirmedHashWithProRegTxHash` mezőkkel dolgozik;
3. közvetlenül a `CalculateQuorum()` és – ahol lánckontextus szükséges – a `GetAllQuorumMembers()`/`ComputeQuorumMembers()` útvonalat hívja;
4. a Core `LLMQParams` struktúráját használja;
5. a kiválasztás után külön fault/network schedule-t alkalmaz a DKG-fázisokra;
6. CSV és JSONL eredményt ír, seed/config/build commit mezőkkel.

Két mód szükséges:

- **selection-only:** 15 000 MN × sok százezer ciklus gyors statisztikához;
- **phase model:** a valódi DKG state machine eseményeivel vagy vékony adapterével, kisebb számú, részletes futáshoz.

A DKG kriptográfiai CPU/memória méréshez ne analitikus becslés legyen az egyetlen forrás: mikrobenchmarkban valódi BLS contribution, verification vector, share verification és recovery fusson 17/25, 41/60 és a jelenlegi profil mellett.

### 5.2. Determinisztikus inputok

MN-populációk: 150, 300, 500, 1 500, 5 000, 10 000, 15 000.

Minden szcenárió legalább:

- 10 000 quorum selection seed/populáció páronként;
- ritka safety-tail eseménynél adaptív futás legalább 95%-os konfidenciaintervallummal;
- reprodukálható master seed;
- azonos seedek Q25 és Q60 páros összevetéséhez.

MN metaadat:

- `operator_id`, `collateral_owner_id`;
- `provider_id`, `asn_id`, `region_id`;
- verzió;
- availability Markov-state;
- latency/loss distribution;
- adversarial group.

### 5.3. Fault matrix

| Család | Értékek |
|---|---|
| független offline | 5, 10, 15, 20, 25, 30% |
| provider kiesés | top-1, top-2, súlyozott 10/20/30% |
| ASN kiesés | top-1, top-3, régión belüli korrelált |
| flapping | 1/5/15 perces on/off; fázishatárhoz igazított |
| operator/collateral koncentráció | 25, 33, 40% |
| DKG delay | fázisidő 25/50/90/110%-a; heavy-tail |
| packet loss modell | 0.1/1/3/5/10%, burst loss |
| mixed version | 10/25/40/50% legacy, mindkét irányú kompatibilitás |
| lifecycle | restart, crash, db restore, reindex, reindex-chainstate |
| adversarial | targeted withholding, equivocation, eclipse-szerű group isolation |

Koncentráció esetén két külön modellt kell futtatni:

- egy operator sok collateral/MN fölött;
- sok látszólag külön operator ugyanazon provider/ASN failure domainben.

### 5.4. Metrikák

Selection:

- MN selection frequency és max deviation;
- chi-square/K-S jellegű uniformitásvizsgálat;
- egymást követő quorumok Jaccard overlapje;
- operator/provider/ASN darabszám és Herfindahl-index;
- adversarial tagok eloszlása és tail percentilisei.

DKG/liveness:

- commitment success rate;
- valid member count histogram;
- `P(valid < minSize)`;
- `P(valid >= minSize && valid < threshold)`;
- signable quorum arány DKG után;
- signing latency p50/p95/p99/p99.9;
- timeout és recovery próbák.

Safety:

- `P(adversarial >= threshold)`;
- két konfliktusos threshold-halmaz létrehozhatósága;
- minimum metszetben levő adversarial tagok;
- operator- és failure-domain-kondicionált kockázat;
- eredmény Wilson/Clopper-Pearson intervallummal, ne csak pontbecsléssel.

Erőforrás:

- BLS CPU idő/fázis és signature;
- peak RSS;
- DKG message count és byte;
- quorumonkénti és napi bandwidth/node;
- DB növekedés;
- reconnect/recovery burst.

PoSe:

- első kieséstől penaltyig és banig eltelt blokkok/idő;
- téves pozitív büntetés;
- egyszerre bannolt populáció;
- recovery/revival idő;
- rewardból kiesett MN-blockok és várható reward-hatás.

### 5.5. A-réteg elfogadási kapuk

A konkrét számokat a baseline mérés után kell lefagyasztani, de minimum:

- nincs seedfüggő, reprodukálhatatlan eredmény;
- selection frequency eltérés magyarázható statisztikai tartományban;
- 15% független offline mellett Q60 DKG success ≥ 99.9%;
- 20% offline mellett publikált p99/p99.9 liveness eredmény, és nincs rejtett silent success;
- 25/33/40% koncentrációnál explicit adversarial-threshold tail;
- provider/ASN kiesésnél PoSe blast radius számszerű;
- a Q60 erőforrásigénye commodity 2 vCPU/4 GB node-on belefér a mért DKG ablakba legalább 2× időtartalékkal.

Az első 99.9%-os cél javasolt induló gate, nem consensus igazság; valós baseline után governance/release döntéssel rögzítendő.

## 6. B réteg – regtest 8–10 valódi operatorral

### 6.1. Topológia

- 8–10 fizikai operator;
- operatoronként 2–4 Core instance, összesen 20–30 logikai MN;
- külön miner/controller node;
- valós BLS operator key minden logikai MN-hez;
- egyedi datadir, port és collateral;
- NTP/óraeltérés monitorozás.

Regtesten `-llmqtestparams`/dedikált test-only profil használható gyorsításhoz. Mainnet paramétert nem szabad emiatt megváltoztatni. A profilváltás tesztjéhez legacy és V2 test LLMQ típus kell, fix activation heighttal.

### 6.2. Tesztsor

1. Baseline: teljes ProReg/ProUpServ, két sikeres DKG, folyamatos ChainLock.
2. Aktiváció `H`:
   - `H-1` CLSIG legacy típussal valid;
   - `H` és `H+1` V2-vel valid;
   - keresztprofil aláírás mindkét irányban invalid.
3. Historical verification:
   - régi CLSIG ellenőrzés tip `H+100` mellett;
   - block/coinbase bestCL validation;
   - RPC `verifychainlock`.
4. Restart/reindex:
   - normál restart;
   - `-reindex-chainstate`;
   - `-reindex`;
   - quorum DB törlés nélkül és támogatott recovery útvonallal;
   - minden esetben ugyanaz a historical eredmény.
5. 50/50 partíció:
   - egyik oldal se tudjon V2 thresholdot elérni;
   - reconnect után egy ág nyerjen, konfliktusevidence nélkül.
6. 60/40 partíció:
   - Q60/41 esetén a 60%-os oldal csak 36 tag lenne, tehát puszta 60/40 tagszétosztás nem ér thresholdot; ezt explicit ellenőrizni kell;
   - ha a kiválasztott quorum eloszlása eltér a hálózati node-aránytól, azt naplózzuk.
7. CLSIG reorder/delay:
   - magasabb CLSIG előbb;
   - ugyanazon height két eltérő valid teszt-signature;
   - ismeretlen block hashhez érkező CLSIG, majd késői header/block.
8. Node-kiesés:
   - 1, 3, 10, 16, 19, 20 quorumtag;
   - DKG alatt és DKG után külön.
9. Mixed version:
   - pre-activation legacy többség;
   - activation után 10/25/40% legacy;
   - legacy node nem fogadhat el félreértelmezett V2 signature-t.
10. PoSe:
   - szándékos contribution hiány;
   - két közeli DKG fail;
   - penalty gyógyulás;
   - ban és revival;
   - reward eligibility ellenőrzés.
11. Conflict persistence:
   - mindkét evidence hash lekérhető;
   - restart, reindex-chainstate, reindex után változatlan;
   - duplikált beküldés idempotens.

### 6.3. Automatizálás

A Dash functional frameworköt kell bővíteni:

- `feature_llmq_chainlocks.py` új activation/historical esetekkel;
- új `feature_llmq_chainlocks_profiles.py`;
- új `feature_llmq_chainlocks_conflict_persistence.py`;
- a meglévő `feature_llmq_dkgerrors.py` PoSe-assertokkal;
- a meglévő `feature_llmq_data_recovery.py` V2 quorum/key recoveryvel.

Minden teszt archiválja:

- node config és build hash;
- `debug.log` monotonic timestamp mellett;
- `quorum list/info/dkgstatus`;
- `getbestchainlock`, conflict RPC;
- block headers, deterministic MN list diff;
- hálózati partíció idővonala.

## 7. C réteg – 20–40 node-os Docker hálózati emuláció

### 7.1. Felépítés

Javasolt Compose-generátor, nem kézzel duplikált 40 service:

- `controller`: Python test orchestrator;
- `miner`;
- `mn01..mn40`;
- opcionális `observer`;
- provider bridge hálózatok: `provider_a`, `provider_b`, `provider_c`, `provider_d`;
- minden Core container `NET_ADMIN` capabilityt csak a netemhez kapjon;
- read-only image, külön named volume/datadir;
- build image a vizsgált commit hashével címkézve.

Linux containerben `tc qdisc netem`, partícióhoz `iptables/nftables` vagy toxiproxy használható. Docker Desktop WSL2 környezetben először capability- és qdisc-smoke test kell.

### 7.2. Fault injection

- latency: 20/50/100/250/500/1000 ms, jitterrel;
- packet loss: 0.1/1/3/5/10%, burst;
- reorder: 1/5/20%;
- provider group teljes leválasztása;
- kétirányú és aszimmetrikus partíció;
- 5/10/20 node restart storm;
- staggered reconnect;
- CPU és memória limit/throttling;
- blokkok versenyeztetése két minerrel;
- recovered signature/CLSIG relay késleltetése és reorder;
- teszt-only RPC/P2P injectorral konfliktusos, kriptográfiailag valid CLSIG.

### 7.3. Kötelező szcenáriók

| ID | Szcenárió | Elvárt eredmény |
|---|---|---|
| D01 | 40 node baseline | DKG és CL stabil, nincs PoSe |
| D02 | 100 ms/1% loss | gate-en belüli latency és DKG |
| D03 | top provider kiesés | blast radius és PoSe mérve |
| D04 | 50/50 partíció | nincs két valid CL |
| D05 | 60/40 partíció | profil matematikája szerinti liveness |
| D06 | 20-node restart storm | recovery, nincs stale/double vote |
| D07 | CLSIG reorder | monoton best CL, evidence helyes |
| D08 | két valid konfliktus | mindkettő perzisztál, safety alert |
| D09 | activation közbeni partíció | signed-height resolver azonos |
| D10 | mixed binary | kompatibilitási mátrix szerint fail/operate |

### 7.4. Megfigyelhetőség

- Prometheus textfile/OpenMetrics endpoint vagy JSON RPC scraper;
- container CPU/RSS/net I/O;
- DKG phase event és message counters;
- CLSIG/recovered-sig timeline;
- PoSe penalty diff blokkonként;
- egységes run ID és fault-event ID;
- pcap csak célzott futásnál, titkos kulcs nélkül.

## 8. D réteg – testnet és nem-consensus shadow mode

### 8.1. Shadow mode szabályai

A shadow mód semmilyen consensus vagy relay döntést nem változtathat:

- nem ír alá és nem relayel V2 CLSIG-et;
- nem változtat `validMembers`, PoSe, chain selection, mempool vagy reward state-et;
- nem választ profilt live MN count alapján;
- ugyanabból a historical chain state-ből kiszámolja a jelölt Q60 tagokat;
- az eredményt külön namespace/DB/metric alatt tartja;
- kikapcsolása teljesen hatástalan a node működésére.

### 8.2. Mit mérjen

- minden V2 DKG ciklus jelölt taglistája;
- tagok verziója, elérhetősége és mérhető failure domainje;
- fázisonként látott message readiness;
- becsült `validMembers`, `minSize=44` teljesülése;
- `threshold=41` elérési idő;
- provider/ASN/operator koncentráció;
- legacy és V2 ugyanazon időablakra vett liveness összevetése;
- „would sign / would fail / insufficient data” eredmény;
- PoSe „would punish” csak telemetria, soha nem state transition.

ASN/provider címkézéshez privacy review kell. Publikus IP-ből származtatott ASN tárolása aggregált legyen; operator mapping csak önkéntes vagy belső tesztadatból.

### 8.3. Shadow acceptance

Legalább:

- 4 hét és legalább 100 teljes DKG ciklus;
- nincs consensus-state diff shadow on/off node-ok között;
- Q60 minSize success rate és signing latency teljesíti az előre rögzített gate-et;
- nincs megmagyarázatlan selection divergence az azonos tipen álló node-ok között;
- minden divergencehez megvan base block, DMN list hash, modifier és build hash.

## 9. Fork-reprodukció a megadott 105632/105633 ponton

Külön incident fixture szükséges:

- parent 105632: `775700a2b3f452b710a001cf175dc1f5cdff96d9b8d97d7f75aa0bb9f78ed9d8`
- seed ág 105633: `2652d357c76b9bec761b0f7331b6c324e37dae8fcc5e42f012c650af09ba3ca4`
- alternatív blokk: `c565cbdb8a9208613d3f767014de1d060dbb681f1d03004338d13c28e94d9cc3`

Szükséges adatcsomag:

- mindkét blokk és legalább 2 teljes DKG ciklusnyi ancestor;
- `protx diff/list` a quorum base/work blockokon;
- mined final commitments;
- mindkét recovered signature/CLSIG nyers bájtja, ha elérhető;
- érintett node-ok `llmq`, `chainlocks`, `net`, `bls` logja;
- node verzió, BLS scheme state, restart/reindex előzmény;
- peers és first-seen idővonal.

Reprodukció:

1. azonos parentből két izolált chain;
2. mindkét oldalon quorum selection dump;
3. request ID, resolved type, quorum hash, sign hash összevetés;
4. signature share források és overlap;
5. ágak újracsatlakoztatása CLSIG mindkét sorrendjében;
6. restart az első recovered sig után;
7. reindex/reindex-chainstate;
8. ellenőrizni, hogy a konfliktus:
   - ugyanazon quorum két msgHash-e;
   - eltérő quorum selection;
   - eltérő BLS state/scheme;
   - vagy hibás persistence/recovery következménye.

Pass/fail: az incident csak akkor tekinthető megmagyarázottnak, ha byte-szinten reprodukálható vagy a két sign hash és a share/tag eredet alapján egyetlen konkrét okra szűkíthető.

## 10. CI, eredményformátum és release gate

### 10.1. CI szintek

- PR: unit resolver, profile boundaries, DB/evidence, rövid selection smoke.
- Nightly: 150–1 500 MN Monte Carlo, functional activation/restart.
- Weekly: 5 000–15 000 MN sweep, Docker 20/40 node fault matrix.
- Release candidate: teljes regtest operator drill, shadow report, incident regression.

### 10.2. Gépileg feldolgozható futási manifest

Minden run:

```json
{
  "schema": 1,
  "core_commit": "fd75a691...",
  "profile": {"type": "candidate_q60", "size": 60, "minSize": 44, "threshold": 41},
  "population": 15000,
  "seed": 123456,
  "scenario": "asn_top3_partition",
  "result": "pass"
}
```

### 10.3. Go/no-go kapuk

No-go bármelyik esetben:

- historical legacy CLSIG az aktiváció után nem ellenőrizhető;
- két azonos signed heighthez tartozó valid konfliktus nem marad tartósan bizonyítható;
- azonos chain state és build mellett eltérő resolver/selection;
- shadow mód consensus-state-et módosít;
- Q60 DKG minimum vagy signing latency nem teljesíti az előre rögzített gate-et;
- provider/ASN hiba tömeges, elfogadhatatlan PoSe bant okoz;
- mixed version vagy restart során double-vote keletkezik;
- resource p99 túllépi a DKG fázis időkeretét.

## 11. Javasolt végrehajtási sorrend

1. Incident evidence összegyűjtése és a 105633 fixture elkészítése.
2. Paraméter-invariáns unit teszt, amely kiírja/ellenőrzi a mainnet ChainLock tényleges `n/min/t` értékét; consensus módosítás nélkül.
3. Determinisztikus selection-only C++ harness.
4. DKG/BLS mikrobenchmark és PoSe modell.
5. Conflict-evidence adattárolási terv és teszt-first prototípus külön ágon.
6. Signed-height resolver unit/functional specifikáció.
7. Regtest profile activation és historical verification.
8. 20-node, majd 40-node Docker fault lab.
9. Testnet shadow telemetry.
10. Mért eredmények alapján Q25/Q60 döntési jegyzőkönyv.
11. Csak ezután külön consensus release implementáció, audit és aktiváció.

## 12. Első sprint konkrét deliverable-jei

- `llmq_scale_simulator` minimal viable harness 150/1 500/15 000 populációval;
- Q25 és Q60 selection/concentration CSV;
- DKG success modell 5–30% offline mellett;
- PoSe penalty timeline report;
- resolver boundary unit teszt specifikáció;
- conflict evidence DB schema és RPC schema;
- 20-node Compose smoke test;
- 105633 incident adat-checklist és reprodukciós runbook;
- egy rövid, számszerű go/no-go dashboard.

Ez a sorrend választ ad a legsürgősebb safety kérdésre anélkül, hogy az első körben mainnet vagy consensus paraméterhez nyúlnánk.
