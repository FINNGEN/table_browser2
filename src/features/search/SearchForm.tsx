import { useState } from "react";
import { useNavigate, useLocation, Link } from "react-router-dom";

export const SearchForm = () => {
  const [value, setValue] = useState("");
  const navigate = useNavigate();

  const handleSubmit = (e: any) => {
    e.preventDefault();
    navigate(`/results/${value}`);
  };

  const { pathname } = useLocation();
  const top = !pathname.startsWith("/results");

  return (
    <div style={{ paddingBottom: "10px" }}>
      <form style={{ display: "inline-block" }} onSubmit={handleSubmit}>
        <label>
          <input
            style={{ width: "30ch" }}
            type="text"
            value={value}
            onChange={(e) => {
              setValue(e.target.value);
            }}
            placeholder={`show all results for a gene or variant`}
          />
        </label>
        <input type="submit" value="go" />
      </form>
      <span style={{ padding: "20px" }}>or</span>
      <Link
        to="/"
        style={
          top ? { color: "#777777", cursor: "not-allowed" } : { color: "black" }
        }
      >
        show top results
      </Link>
    </div>
  );
};
