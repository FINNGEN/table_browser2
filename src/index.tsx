import { render } from "react-dom";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Provider } from "react-redux";
import ReactTooltip from "react-tooltip";
import { SearchForm } from "./features/search/SearchForm";
import { ResultTable } from "./features/table/ResultTable";
import config from "../config.json";

import store from "./app/store";

render(
  <Provider store={store}>
    <BrowserRouter>
      <div style={{ padding: "10px" }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            paddingBottom: "10px",
          }}
        >
          <ReactTooltip
            place="left"
            offset={{ top: -225 }}
            arrowColor="transparent"
            html={true}
          />
          <span className="title">
            FinnGen freeze 9 coding variant result browser
          </span>
          <span className="help" data-tip={config.help}>
            ?
          </span>
        </div>
        <SearchForm />
        <Routes>
          <Route path="/" element={<ResultTable />} />
          <Route path="/results/:query" element={<ResultTable />} />
        </Routes>
      </div>
    </BrowserRouter>
  </Provider>,
  document.getElementById("reactEntry")
);
