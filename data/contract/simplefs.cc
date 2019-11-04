#include "xchain/xchain.h"

struct S3 : public xchain::Contract {};

DEFINE_METHOD(S3, initialize) {
    xchain::Context* ctx = self.context();
    ctx->ok("initialize succeed");
}

DEFINE_METHOD(S3, put) {
    xchain::Context* ctx = self.context();
    const std::string& key = ctx->arg("key");
    const std::string& value = ctx->arg("value");
    ctx->put_object(key, value); 
    ctx->ok(key);
}

DEFINE_METHOD(S3, get) {
    xchain::Context* ctx = self.context();
    const std::string& key = ctx->arg("key");
    std::string value;
    if (ctx->get_object(key, &value)) {
        ctx->ok(value);
    } else {
        ctx->error("key not found");
    }
}

DEFINE_METHOD(S3, scan) {
    xchain::Context* ctx = self.context();
    const std::string& prefix = ctx->arg("prefix");
    auto iter = ctx->new_iterator(prefix, prefix + "\xff");
    std::string buf;
    while (iter->next()) {
	    std::pair<std::string, std::string> pair;
        iter->get(&pair);
        buf += pair.first;
        printf("iter key:%s\n", pair.first.c_str());
        buf += "\n";	
    }
    printf("final buf:%s\n", buf.c_str());
    ctx->ok(buf);
}

