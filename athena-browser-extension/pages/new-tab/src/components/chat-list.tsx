import DeleteIcon from "../icons/delete.svg";

import styles from "./home.module.scss";

import { useChatStore } from "../store";

import Locale from "../locales";
import { useNavigate } from "react-router-dom";
import { Path } from "../constant";

import React from "react";
import { showConfirm } from "./ui-lib";
import { useMobileScreen } from "../utils";
import clsx from "clsx";

export function ChatItem(props: {
  onClick?: () => void;
  onDelete?: () => void;
  title: string;
  count: number;
  time: string;
  selected: boolean;
  id: string;
  index: number;
  narrow?: boolean;
}) {
  const currentPath = "";
  const content = (
    <div
      className={clsx(styles["chat-item"], {
        [styles["chat-item-selected"]]: props.selected,
      })}
      onClick={props.onClick}
      ref={undefined as unknown as React.Ref<HTMLDivElement>}
      title={`${props.title}\n${Locale.ChatItem.ChatItemCount(props.count)}`}
    >
      {props.narrow ? (
        <div className={styles["chat-item-narrow"]}>
          <div className={clsx(styles["chat-item-avatar"], "no-dark")}>
            <div className={styles["chat-item-avatar-placeholder"]}></div>
          </div>
          <div className={styles["chat-item-narrow-count"]}>{props.count}</div>
        </div>
      ) : (
        <>
          <div className={styles["chat-item-title"]}>{props.title}</div>
          <div className={styles["chat-item-info"]}>
            <div className={styles["chat-item-count"]}>
              {Locale.ChatItem.ChatItemCount(props.count)}
            </div>
            <div className={styles["chat-item-date"]}>{props.time}</div>
          </div>
        </>
      )}
      <div
        className={styles["chat-item-delete"]}
        onClickCapture={(e) => {
          props.onDelete?.();
          e.preventDefault();
          e.stopPropagation();
        }}
      >
        <DeleteIcon />
      </div>
    </div>
  );
  return content;
}

export function ChatList(props: { narrow?: boolean }) {
  const sessions = useChatStore((s) => s.sessions);
  const selectedIndex = useChatStore((s) => s.currentSessionIndex);
  const selectSession = useChatStore((s) => s.selectSession);
  const deleteSession = useChatStore((s) => s.deleteSession);
  const navigate = useNavigate();
  const isMobileScreen = useMobileScreen();

  return (
    <div className={styles["chat-list"]}>
      {sessions.map((item, i) => (
        <ChatItem
          title={item.topic}
          time={new Date(item.lastUpdate).toLocaleString()}
          count={item.messages.length}
          key={item.id}
          id={item.id}
          index={i}
          selected={i === selectedIndex}
          onClick={() => {
            navigate(Path.Chat);
            selectSession(i);
          }}
          onDelete={async () => {
            if (
              (!props.narrow && !isMobileScreen) ||
              (await showConfirm(Locale.Home.DeleteChat))
            ) {
              deleteSession(i);
            }
          }}
          narrow={props.narrow}
        />
      ))}
    </div>
  );
}
