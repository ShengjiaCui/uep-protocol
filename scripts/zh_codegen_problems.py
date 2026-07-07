#!/usr/bin/env python3
"""UEP 原生中文 codegen 题库（A5 作者源，非第三方数据——自写 Apache-2.0，可入库）。

每题五字段：
  id          题号
  prompt      HumanEval 形态题面：英文函数签名 + **中文 docstring**（含示例），模型补全函数体
  entry_point 待实现函数名
  solution    参考解（完整函数；仅供参考解自测，不入 items.jsonl）
  test_code   HumanEval check(candidate) 约定：定义 check，A1 scorer 拼 candidate+test_code+check(entry_point)

放 scripts/（可 import）而非 examples/zh-codegen/（连字符不可作 Python 包名）；
生成的 items.jsonl/manifest.json 落 examples/zh-codegen/。
"""

PROBLEMS: list[dict[str, str]] = [
    {
        "id": "zh-codegen-0001",
        "entry_point": "two_sum",
        "prompt": (
            "def two_sum(nums, target):\n"
            '    """给定一个整数数组 nums 和一个目标值 target，返回和为 target 的两个元素的下标，\n'
            "    以列表形式按升序返回。保证恰有一个解，且同一个元素不能使用两次。\n"
            "    示例：two_sum([2, 7, 11, 15], 9) 返回 [0, 1]。\n"
            '    """\n'
        ),
        "solution": (
            "def two_sum(nums, target):\n"
            "    seen = {}\n"
            "    for i, x in enumerate(nums):\n"
            "        if target - x in seen:\n"
            "            return [seen[target - x], i]\n"
            "        seen[x] = i\n"
            "    return []\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            "    assert candidate([2, 7, 11, 15], 9) == [0, 1]\n"
            "    assert candidate([3, 2, 4], 6) == [1, 2]\n"
            "    assert candidate([3, 3], 6) == [0, 1]\n"
            "    assert candidate([-1, -2, -3, -4], -7) == [2, 3]\n"
        ),
    },
    {
        "id": "zh-codegen-0002",
        "entry_point": "is_palindrome",
        "prompt": (
            "def is_palindrome(s):\n"
            '    """判断字符串 s 是否为回文（正读与反读相同），只考虑字母与数字并忽略大小写，\n'
            "    其余字符一律跳过。空字符串视为回文，返回布尔值。\n"
            '    示例：is_palindrome("A man, a plan, a canal: Panama") 返回 True。\n'
            '    """\n'
        ),
        "solution": (
            "def is_palindrome(s):\n"
            "    t = [c.lower() for c in s if c.isalnum()]\n"
            "    return t == t[::-1]\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            '    assert candidate("A man, a plan, a canal: Panama") is True\n'
            '    assert candidate("race a car") is False\n'
            '    assert candidate("") is True\n'
            '    assert candidate("Ab_a") is True\n'
        ),
    },
    {
        "id": "zh-codegen-0003",
        "entry_point": "count_vowels",
        "prompt": (
            "def count_vowels(s):\n"
            '    """统计字符串 s 中英文元音字母（a、e、i、o、u，不区分大小写）的个数，返回整数。\n'
            '    示例：count_vowels("Hello World") 返回 3。\n'
            '    """\n'
        ),
        "solution": (
            "def count_vowels(s):\n" "    return sum(1 for c in s.lower() if c in 'aeiou')\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            '    assert candidate("Hello World") == 3\n'
            '    assert candidate("") == 0\n'
            '    assert candidate("XYZ") == 0\n'
            '    assert candidate("AEIOU") == 5\n'
        ),
    },
    {
        "id": "zh-codegen-0004",
        "entry_point": "factorial",
        "prompt": (
            "def factorial(n):\n"
            '    """返回非负整数 n 的阶乘 n!（即 1×2×…×n），规定 0! = 1。\n'
            "    示例：factorial(5) 返回 120。\n"
            '    """\n'
        ),
        "solution": (
            "def factorial(n):\n"
            "    result = 1\n"
            "    for i in range(2, n + 1):\n"
            "        result *= i\n"
            "    return result\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            "    assert candidate(0) == 1\n"
            "    assert candidate(1) == 1\n"
            "    assert candidate(5) == 120\n"
            "    assert candidate(10) == 3628800\n"
        ),
    },
    {
        "id": "zh-codegen-0005",
        "entry_point": "fib",
        "prompt": (
            "def fib(n):\n"
            '    """返回斐波那契数列的第 n 项（从 0 开始计数）：fib(0)=0，fib(1)=1，\n'
            "    此后每项为前两项之和。保证 n 为非负整数。\n"
            "    示例：fib(7) 返回 13。\n"
            '    """\n'
        ),
        "solution": (
            "def fib(n):\n"
            "    a, b = 0, 1\n"
            "    for _ in range(n):\n"
            "        a, b = b, a + b\n"
            "    return a\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            "    assert candidate(0) == 0\n"
            "    assert candidate(1) == 1\n"
            "    assert candidate(7) == 13\n"
            "    assert candidate(10) == 55\n"
        ),
    },
    {
        "id": "zh-codegen-0006",
        "entry_point": "reverse_words",
        "prompt": (
            "def reverse_words(s):\n"
            '    """反转字符串 s 中单词的顺序：单词以空格分隔，返回反转后的字符串，\n'
            "    单词之间以单个空格连接，并去除首尾多余空格。\n"
            '    示例：reverse_words("  hello   world  ") 返回 "world hello"。\n'
            '    """\n'
        ),
        "solution": ("def reverse_words(s):\n" "    return ' '.join(reversed(s.split()))\n"),
        "test_code": (
            "def check(candidate):\n"
            '    assert candidate("  hello   world  ") == "world hello"\n'
            '    assert candidate("the sky is blue") == "blue is sky the"\n'
            '    assert candidate("单词") == "单词"\n'
            '    assert candidate("   ") == ""\n'
        ),
    },
    {
        "id": "zh-codegen-0007",
        "entry_point": "is_prime",
        "prompt": (
            "def is_prime(n):\n"
            '    """判断整数 n 是否为素数（大于 1 且只能被 1 和自身整除），返回布尔值。\n'
            "    小于 2 的整数一律不是素数。\n"
            "    示例：is_prime(13) 返回 True，is_prime(1) 返回 False。\n"
            '    """\n'
        ),
        "solution": (
            "def is_prime(n):\n"
            "    if n < 2:\n"
            "        return False\n"
            "    i = 2\n"
            "    while i * i <= n:\n"
            "        if n % i == 0:\n"
            "            return False\n"
            "        i += 1\n"
            "    return True\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            "    assert candidate(1) is False\n"
            "    assert candidate(2) is True\n"
            "    assert candidate(13) is True\n"
            "    assert candidate(15) is False\n"
            "    assert candidate(0) is False\n"
        ),
    },
    {
        "id": "zh-codegen-0008",
        "entry_point": "gcd",
        "prompt": (
            "def gcd(a, b):\n"
            '    """返回两个正整数 a 与 b 的最大公约数（能同时整除 a 和 b 的最大正整数）。\n'
            "    示例：gcd(12, 18) 返回 6。\n"
            '    """\n'
        ),
        "solution": (
            "def gcd(a, b):\n" "    while b:\n" "        a, b = b, a % b\n" "    return a\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            "    assert candidate(12, 18) == 6\n"
            "    assert candidate(17, 5) == 1\n"
            "    assert candidate(100, 10) == 10\n"
            "    assert candidate(7, 7) == 7\n"
        ),
    },
    {
        "id": "zh-codegen-0009",
        "entry_point": "dedup",
        "prompt": (
            "def dedup(items):\n"
            '    """对列表 items 去重，保留每个元素**首次出现**的顺序，返回新列表。\n'
            "    示例：dedup([1, 3, 1, 2, 3]) 返回 [1, 3, 2]。\n"
            '    """\n'
        ),
        "solution": (
            "def dedup(items):\n"
            "    seen = set()\n"
            "    out = []\n"
            "    for x in items:\n"
            "        if x not in seen:\n"
            "            seen.add(x)\n"
            "            out.append(x)\n"
            "    return out\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            "    assert candidate([1, 3, 1, 2, 3]) == [1, 3, 2]\n"
            "    assert candidate([]) == []\n"
            '    assert candidate(["a", "a", "b"]) == ["a", "b"]\n'
            "    assert candidate([5, 5, 5]) == [5]\n"
        ),
    },
    {
        "id": "zh-codegen-0010",
        "entry_point": "word_count",
        "prompt": (
            "def word_count(s):\n"
            '    """统计字符串 s 中每个单词出现的次数，单词以空白分隔，返回字典（单词→次数）。\n'
            '    示例：word_count("a b a") 返回 {"a": 2, "b": 1}。\n'
            '    """\n'
        ),
        "solution": (
            "def word_count(s):\n"
            "    counts = {}\n"
            "    for w in s.split():\n"
            "        counts[w] = counts.get(w, 0) + 1\n"
            "    return counts\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            '    assert candidate("a b a") == {"a": 2, "b": 1}\n'
            '    assert candidate("") == {}\n'
            '    assert candidate("你好 世界 你好") == {"你好": 2, "世界": 1}\n'
        ),
    },
    {
        "id": "zh-codegen-0011",
        "entry_point": "binary_search",
        "prompt": (
            "def binary_search(nums, target):\n"
            '    """在**升序**整数列表 nums 中二分查找 target，返回其下标；不存在则返回 -1。\n'
            "    示例：binary_search([1, 3, 5, 7, 9], 7) 返回 3。\n"
            '    """\n'
        ),
        "solution": (
            "def binary_search(nums, target):\n"
            "    lo, hi = 0, len(nums) - 1\n"
            "    while lo <= hi:\n"
            "        mid = (lo + hi) // 2\n"
            "        if nums[mid] == target:\n"
            "            return mid\n"
            "        elif nums[mid] < target:\n"
            "            lo = mid + 1\n"
            "        else:\n"
            "            hi = mid - 1\n"
            "    return -1\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            "    assert candidate([1, 3, 5, 7, 9], 7) == 3\n"
            "    assert candidate([1, 3, 5, 7, 9], 4) == -1\n"
            "    assert candidate([], 1) == -1\n"
            "    assert candidate([42], 42) == 0\n"
        ),
    },
    {
        "id": "zh-codegen-0012",
        "entry_point": "is_anagram",
        "prompt": (
            "def is_anagram(s, t):\n"
            '    """判断字符串 s 与 t 是否互为变位词（由完全相同的字符按不同顺序组成），\n'
            "    区分大小写，返回布尔值。长度不同必不是变位词。\n"
            '    示例：is_anagram("listen", "silent") 返回 True。\n'
            '    """\n'
        ),
        "solution": ("def is_anagram(s, t):\n" "    return sorted(s) == sorted(t)\n"),
        "test_code": (
            "def check(candidate):\n"
            '    assert candidate("listen", "silent") is True\n'
            '    assert candidate("rat", "car") is False\n'
            '    assert candidate("", "") is True\n'
            '    assert candidate("aabb", "bbaa") is True\n'
            '    assert candidate("a", "ab") is False\n'
        ),
    },
    {
        "id": "zh-codegen-0013",
        "entry_point": "flatten",
        "prompt": (
            "def flatten(nested):\n"
            '    """将一个二维列表 nested（列表的列表）展平为一维列表，保持原有顺序。\n'
            "    示例：flatten([[1, 2], [3], [], [4, 5]]) 返回 [1, 2, 3, 4, 5]。\n"
            '    """\n'
        ),
        "solution": (
            "def flatten(nested):\n"
            "    out = []\n"
            "    for row in nested:\n"
            "        for x in row:\n"
            "            out.append(x)\n"
            "    return out\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            "    assert candidate([[1, 2], [3], [], [4, 5]]) == [1, 2, 3, 4, 5]\n"
            "    assert candidate([]) == []\n"
            "    assert candidate([[], []]) == []\n"
            '    assert candidate([["a"], ["b", "c"]]) == ["a", "b", "c"]\n'
        ),
    },
    {
        "id": "zh-codegen-0014",
        "entry_point": "sum_digits",
        "prompt": (
            "def sum_digits(n):\n"
            '    """返回非负整数 n 各位数字之和。\n'
            "    示例：sum_digits(1234) 返回 10。\n"
            '    """\n'
        ),
        "solution": (
            "def sum_digits(n):\n"
            "    total = 0\n"
            "    while n > 0:\n"
            "        total += n % 10\n"
            "        n //= 10\n"
            "    return total\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            "    assert candidate(0) == 0\n"
            "    assert candidate(1234) == 10\n"
            "    assert candidate(9) == 9\n"
            "    assert candidate(100) == 1\n"
        ),
    },
    {
        "id": "zh-codegen-0015",
        "entry_point": "move_zeros",
        "prompt": (
            "def move_zeros(nums):\n"
            '    """将列表 nums 中所有的 0 移动到末尾，同时保持非零元素的相对顺序，返回新列表。\n'
            "    示例：move_zeros([0, 1, 0, 3, 12]) 返回 [1, 3, 12, 0, 0]。\n"
            '    """\n'
        ),
        "solution": (
            "def move_zeros(nums):\n"
            "    nonzero = [x for x in nums if x != 0]\n"
            "    return nonzero + [0] * (len(nums) - len(nonzero))\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            "    assert candidate([0, 1, 0, 3, 12]) == [1, 3, 12, 0, 0]\n"
            "    assert candidate([0, 0, 0]) == [0, 0, 0]\n"
            "    assert candidate([1, 2, 3]) == [1, 2, 3]\n"
            "    assert candidate([]) == []\n"
        ),
    },
    {
        "id": "zh-codegen-0016",
        "entry_point": "max_subarray",
        "prompt": (
            "def max_subarray(nums):\n"
            '    """返回非空整数列表 nums 中，连续子数组的最大和（子数组至少含一个元素）。\n'
            "    示例：max_subarray([-2, 1, -3, 4, -1, 2, 1, -5, 4]) 返回 6（子数组 [4, -1, 2, 1]）。\n"
            '    """\n'
        ),
        "solution": (
            "def max_subarray(nums):\n"
            "    best = cur = nums[0]\n"
            "    for x in nums[1:]:\n"
            "        cur = max(x, cur + x)\n"
            "        best = max(best, cur)\n"
            "    return best\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            "    assert candidate([-2, 1, -3, 4, -1, 2, 1, -5, 4]) == 6\n"
            "    assert candidate([1]) == 1\n"
            "    assert candidate([-1, -2, -3]) == -1\n"
            "    assert candidate([5, 4, -1, 7, 8]) == 23\n"
        ),
    },
    {
        "id": "zh-codegen-0017",
        "entry_point": "to_binary",
        "prompt": (
            "def to_binary(n):\n"
            '    """将非负整数 n 转换为不含前导零的二进制字符串（0 转换为 "0"）。\n'
            '    示例：to_binary(13) 返回 "1101"。\n'
            '    """\n'
        ),
        "solution": (
            "def to_binary(n):\n"
            "    if n == 0:\n"
            "        return '0'\n"
            "    bits = ''\n"
            "    while n > 0:\n"
            "        bits = str(n % 2) + bits\n"
            "        n //= 2\n"
            "    return bits\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            '    assert candidate(0) == "0"\n'
            '    assert candidate(13) == "1101"\n'
            '    assert candidate(1) == "1"\n'
            '    assert candidate(8) == "1000"\n'
        ),
    },
    {
        "id": "zh-codegen-0018",
        "entry_point": "is_balanced",
        "prompt": (
            "def is_balanced(s):\n"
            '    """判断只含三种括号 ()[]{} 的字符串 s 是否**正确匹配**：每个左括号都有类型相同的\n'
            "    右括号按正确顺序闭合。空字符串视为匹配，返回布尔值。\n"
            '    示例：is_balanced("{[()]}") 返回 True，is_balanced("([)]") 返回 False。\n'
            '    """\n'
        ),
        "solution": (
            "def is_balanced(s):\n"
            "    pairs = {')': '(', ']': '[', '}': '{'}\n"
            "    stack = []\n"
            "    for c in s:\n"
            "        if c in '([{':\n"
            "            stack.append(c)\n"
            "        elif c in pairs:\n"
            "            if not stack or stack.pop() != pairs[c]:\n"
            "                return False\n"
            "    return not stack\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            '    assert candidate("{[()]}") is True\n'
            '    assert candidate("([)]") is False\n'
            '    assert candidate("") is True\n'
            '    assert candidate("(((") is False\n'
            '    assert candidate("()[]{}") is True\n'
        ),
    },
    {
        "id": "zh-codegen-0019",
        "entry_point": "merge_sorted",
        "prompt": (
            "def merge_sorted(a, b):\n"
            '    """将两个**升序**整数列表 a 与 b 合并为一个升序列表并返回（允许重复元素）。\n'
            "    示例：merge_sorted([1, 3, 5], [2, 4]) 返回 [1, 2, 3, 4, 5]。\n"
            '    """\n'
        ),
        "solution": (
            "def merge_sorted(a, b):\n"
            "    i = j = 0\n"
            "    out = []\n"
            "    while i < len(a) and j < len(b):\n"
            "        if a[i] <= b[j]:\n"
            "            out.append(a[i]); i += 1\n"
            "        else:\n"
            "            out.append(b[j]); j += 1\n"
            "    out.extend(a[i:])\n"
            "    out.extend(b[j:])\n"
            "    return out\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            "    assert candidate([1, 3, 5], [2, 4]) == [1, 2, 3, 4, 5]\n"
            "    assert candidate([], []) == []\n"
            "    assert candidate([1, 1], [1]) == [1, 1, 1]\n"
            "    assert candidate([], [2, 3]) == [2, 3]\n"
        ),
    },
    {
        "id": "zh-codegen-0020",
        "entry_point": "title_case",
        "prompt": (
            "def title_case(s):\n"
            '    """将字符串 s 中每个单词的首字母大写、其余字母小写，单词以单个空格分隔，\n'
            "    保持单词顺序不变。假设输入以单个空格分隔、无首尾空格。\n"
            '    示例：title_case("hello WORLD from uep") 返回 "Hello World From Uep"。\n'
            '    """\n'
        ),
        "solution": (
            "def title_case(s):\n"
            "    return ' '.join(w[:1].upper() + w[1:].lower() for w in s.split(' '))\n"
        ),
        "test_code": (
            "def check(candidate):\n"
            '    assert candidate("hello WORLD from uep") == "Hello World From Uep"\n'
            '    assert candidate("a") == "A"\n'
            '    assert candidate("PYTHON") == "Python"\n'
        ),
    },
]
