import assert from "node:assert/strict";
import { it } from "node:test";
import { Children, createElement, isValidElement, type ReactNode } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { WalletNav } from "../classroom/WalletNav.js";

it("shows disconnect for a connected wallet and connect after disconnect", () => {
  const account = "0x1111111111111111111111111111111111111111";
  const connected = renderToStaticMarkup(createElement(WalletNav, {
    account, onConnect: () => {}, onDisconnect: () => {},
  }));
  assert.match(connected, /Ví 0x1111…1111/);
  assert.match(connected, /Ngắt kết nối/);
  assert.doesNotMatch(connected, /Kết nối ví<\/button>/);

  const disconnected = renderToStaticMarkup(createElement(WalletNav, {
    onConnect: () => {}, onDisconnect: () => {},
  }));
  assert.match(disconnected, /Kết nối ví/);
  assert.doesNotMatch(disconnected, /Ngắt kết nối/);
});

it("runs the disconnect action when the connected wallet button is clicked", () => {
  let disconnected = false;
  const view = WalletNav({
    account: "0x1111111111111111111111111111111111111111",
    onConnect: () => {}, onDisconnect: () => { disconnected = true; },
  });
  const content = Children.toArray(view.props.children)[0];
  assert.ok(isValidElement<{ children?: ReactNode }>(content));
  const button = Children.toArray(content.props.children).find(child => isValidElement<{ onClick?: () => void }>(child) && child.type === "button");
  assert.ok(isValidElement<{ onClick?: () => void }>(button));
  button.props.onClick?.();
  assert.equal(disconnected, true);
});
