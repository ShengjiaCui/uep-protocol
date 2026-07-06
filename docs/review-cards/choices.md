# 【UEP 原型评审卡】原型：choices　协议版本：2.0.0-draft　日期：2026-07-04

> L3 人本验证首次试运行（测试规格书 §⑥）。评审人=用户本人（零背景者缺位的计划降级路径）。
> 口述理解测试（附加）：给未接触者看下方任一渲染样例，能口述"这条评测在考什么、怎么算对"即通过。

## 1. 定义表（照抄 SPEC §3.2）

**task（type="choices"）**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `question` | str | 题干 |
| `options` | list[{`id`: str, `text`: str}] | 选项；`id` 如 `"A"`/`"0"`，保留源习惯 |
| `multi_select` | bool = false | 是否多选 |

正确项不在 task 里——在 **`choice_match` Verifier**（`answer_ids: list[str]`，P2：打分自含，单一事实源）。

## 2. 样例渲染（经试金石 `touchstones/render_choices.py`）

**英文样例（真实切片：MMLU test 第 3 条，id `mmlu-test-0002`）**

```
Find all zeros in the indicated finite field of the given polynomial with coefficients in that field. x^5 + 3x^3 + x^2 + 2x in Z_5

A. 0
B. 1
C. 0,1
D. 0,4
```
正确项：`D`

**中文样例（合成夹具，id `zh_demo_chem_001`）**

```
下列哪种气体是植物光合作用的主要原料之一？

A. 氧气
B. 二氧化碳
C. 氮气
D. 氢气
```
正确项：`B`

> ⚠️ **对模板的显式偏离**：模板要求中文样例也来自真实切片，但当前已接入的三个
> choices 真实数据集（MMLU/ARC/HellaSwag）均为英文。候选中文真实数据集
> CMMLU / C-Eval 许可均为 CC-BY-**NC**（非商业），是否接入需要你裁决（见 Q6）。

## 3. 评审问题（评审人作答）

- **Q1** 字段命名在你的领域看着自然吗？哪个别扭？
  答：
- **Q2** 你领域常见的选择题数据，有装不进这个结构的吗？举例。
  答：
- **Q3** 哪个字段你第一眼理解错了？
  答：
- **Q4** 缺了什么你认为必要的信息？
  答：
- **Q5** 结论：通过 / 有条件通过（条件：＿＿）/ 打回
  答：
- **Q6（本卡附加裁决）** 中文真实 choices 切片：接入 CC-BY-NC 数据集（CMMLU/C-Eval，注明非商业限制）／ 另寻宽松许可中文数据集 ／ 暂以合成中文夹具过渡？
  答：

## 4. 评审人：＿＿＿（领域背景：＿＿＿）　日期：＿＿＿

## 5. 用户终签：＿＿＿
