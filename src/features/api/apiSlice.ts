import {
  createApi,
  fetchBaseQuery,
  BaseQueryFn,
  FetchArgs,
} from "@reduxjs/toolkit/query/react";
import { ApiError, VariantResults } from "../../types/types";

export const apiSlice = createApi({
  reducerPath: "api",
  baseQuery: fetchBaseQuery({ baseUrl: "/api/v1" }) as BaseQueryFn<
    string | FetchArgs,
    unknown,
    ApiError,
    {}
  >,
  endpoints: (builder) => ({
    getVariantResults: builder.query<VariantResults, string>({
      query: (query) => `/results/${query}`,
      transformResponse: (response: VariantResults) => {
        response.results.forEach((result) => {
          result.anno = response.anno[result.variant];
          result.rec_add =
            result.mlogp_rec && result.mlogp_add
              ? result.mlogp_rec - result.mlogp_add
              : null;
        });
        return response;
      },
    }),
    getTopResults: builder.query<VariantResults, void>({
      query: () => `/top`,
      transformResponse: (response: VariantResults) => {
        response.results.forEach((result) => {
          result.anno = response.anno[result.variant];
          result.rec_add =
            result.mlogp_rec && result.mlogp_add
              ? result.mlogp_rec - result.mlogp_add
              : null;
        });
        return response;
      },
    }),
  }),
});

export const { useGetVariantResultsQuery, useGetTopResultsQuery } = apiSlice;
