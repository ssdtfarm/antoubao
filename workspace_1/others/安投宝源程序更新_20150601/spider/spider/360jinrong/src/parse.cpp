#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include <map>
#include "../../common/utils/json_utils.h"
#include "../../common/utils/utils.h"
#include "../../common/spi_utils/spi_utils.h"

using namespace std;

int parsefile(const char *idstr)
{
    char filename[256];
    sprintf(filename, "html/%s", idstr);
    char *buf = readfile(filename);
    if (!buf) {
        return 1;
    }

    string bstr = string(buf);
    free(buf);
    map <string, string> kv;
    kv["site_id"] = "360jinrong";
    kv["project_id"] = idstr;
    kv["borrower"] = "";
    kv["project_name"] = extract(bstr, "class=\"project-main\"", "class=\"info fl\"", "<b>", "</b>");
    kv["borrowing_amount"] = num_util(filternum(extract(bstr, "class=\"info-line\"", "融资金额", "class=\"info\" >", "</span>")));
    kv["loan_period"] = loanperiod_util(extract(bstr, "class=\"key-table-wrap\"", "回购期限", "class=\"info\">", "</em>"));
    kv["release_time"] = "";
    kv["payment_method"] = extract(bstr, "class=\"key-table-wrap\"", "还款方式", "style=\"font-size:16px\" >", "</em>");

    string invstr;
    int invnum = 0;

    sprintf(filename, "html/%s.brec", idstr);
    buf = readfile(filename);
    if (!buf) {
        return 1;
    }   
    string tmps = string(buf);
    string flag("<tr>");
    size_t beg, end;
    beg = tmps.find(flag);

    while ( beg != string::npos )
    {   
        end = tmps.find(flag, beg+flag.size());

        string s;
        if (end != string::npos)
        {   
            s = tmps.substr(beg+flag.size(), end-beg);
        }   
        else
        {   
            s = tmps.substr(beg+flag.size());
        }   

        string uname = extract(s, "<td", "height='25'", ">", "</td>");
        string account = filternum(extract(s, "<td", "<td", ">￥", "</td>"));
        string addtime = extract(s, "</td>", "</td>", ">", "</td>");

        invstr += longtostring(stringtotime(addtime.c_str(), "%Y-%m-%d %H:%M:%S")) + "|" + uname + "|" + account + "|";
        invnum++;

        beg = end;
    }

    kv["investor"] = invstr;
    kv["investors_volume"] = longtostring(invnum);

    printstringmap(kv);

    if (kv["project_id"] == "" || s_atol(kv["borrowing_amount"].c_str()) <= 0) {
        return 1;
    }

    sprintf(filename, "data/%s", idstr);
    return savestringmap(kv, filename);
}

int main(int argc, char *argv[])
{
    if (argc < 2) {
        return 0;
    }
    return parsefile(argv[1]);
}

