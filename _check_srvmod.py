"""Serverside: check module syntax"""
exec(open("modules/qodo_review.py").read())
print("qodo_review syntax OK")
print("QodoReviewModule" in dir())
