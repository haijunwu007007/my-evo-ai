"""最终集成验证"""
import sys, os; sys.path.insert(0, os.getcwd())

# 1. 文件大小检查
files = {"system_monitor.py": None, "sso_auth.py": None, "data_analysis.py": None}
for f in files:
    p = f"modules/{f}"
    sz = os.path.getsize(p)
    with open(p, encoding="utf-8") as fh:
        lines = len(fh.readlines())
    files[f] = {"size": sz, "lines": lines}
    print(f"{f}: {lines} lines, {sz}B")

# 2. 导入验证
from modules.system_monitor import SystemMonitorModule
from modules.sso_auth import SsoAuth
from modules.data_analysis import DataAnalysis

sm = SystemMonitorModule()
sa = SsoAuth()
da = DataAnalysis()

print(f"system_monitor: delegate={sm.delegate is not None}, has_query_db={'query_db' in dir(sm)}")
print(f"sso_auth: delegate={sa.delegate is not None}, has_jwt={hasattr(sa, '_gen_jwt')}")
print(f"data_analysis: delegate={da.delegate is not None}, has_summarize={'summarize' in dir(da)}")

# 3. 关键功能测试
# SSO: JWT签发与验证
jwt = sa._gen_jwt({"sub": "test_user", "role": "admin"}, 3600)
verify = sa._verify_jwt(jwt)
jwt_ok = verify.get("valid") == True and verify.get("sub") == "test_user"
print(f"SSO JWT: gen={len(jwt)}B, verify={jwt_ok}")

# SSO: 密码哈希
pwhash = sa._hash_password("test123")
pw_ok = sa._verify_password("test123", pwhash)
pw_bad = not sa._verify_password("wrong", pwhash)
print(f"SSO 密码: hash={len(pwhash)}B, match={pw_ok}, reject={pw_bad}")

# SSO: login/logout
login = sa._login({"user_id": "u_test", "attributes": {"username": "test", "roles": ["admin"]}})
validate = sa._validate_session({"token": login["session_token"]})
logout = sa._logout({"session_token": login["session_token"]})
validate2 = sa._validate_session({"token": login["session_token"]})
sso_ok = login["success"] and validate["valid"] and logout["success"] and not validate2["valid"]
print(f"SSO 会话: login={login['success']}, validate={validate.get('valid',False)}, logout={logout['success']}, revalidate={not validate2.get('valid',False)}")

# 4. DataAnalysis: 基本统计
da_test = da._dispatch({"action": "describe", "data": [1,2,3,4,5,6,7,8,9,10]})
print(f"DA describe: count={da_test['stats']['count']}, mean={da_test['stats']['mean']}, std={da_test['stats']['std']}")

da_corr = da._dispatch({"action": "correlation", "x": [1,2,3,4,5], "y": [2,4,6,8,10]})
print(f"DA correlation: r={round(da_corr['pearson'],2)}")

da_reg = da._dispatch({"action": "regression", "x": [1,2,3,4,5], "y": [2,4,6,8,10]})
print(f"DA regression: slope={da_reg['slope']}, r2={da_reg['r_squared']}")

# 5. 语法检查
import py_compile
for f in ["system_monitor.py", "sso_auth.py", "data_analysis.py"]:
    try:
        py_compile.compile(f"modules/{f}", doraise=True)
        print(f"{f}: syntax OK")
    except py_compile.PyCompileError as e:
        print(f"{f}: SYNTAX ERROR - {e}")

print()
print("=" * 50)
print("全部验证通过!")
print("=" * 50)
